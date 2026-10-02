/* SPDX-License-Identifier: Apache-2.0 */
#include <atomic>
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <thread>

#define ALOGE(...) ((void)0)
#define ALOGD(...) ((void)0)
namespace ndk {
struct ScopedAStatus {
    int error = 0;
    static ScopedAStatus ok() { return {}; }
    static ScopedAStatus fromServiceSpecificError(int error) { return {error}; }
    bool isOk() const { return error == 0; }
    std::string getDescription() const { return "test"; }
};
}
struct HardwareAuthToken { int challenge = 42; };
using hw_auth_token_t = HardwareAuthToken;
static void translate(const HardwareAuthToken& input, hw_auth_token_t& output) {
    output = input;
}
struct LockoutTracker {
    enum class LockoutMode { kNone, kPermanent };
    LockoutMode mode = LockoutMode::kNone;
    LockoutMode getMode() { return mode; }
    void reset(bool) { mode = LockoutMode::kNone; }
};
struct Callback {
    std::mutex mutex;
    std::condition_variable condition;
    int calls = 0;
    ndk::ScopedAStatus onLockoutCleared() {
        std::lock_guard<std::mutex> lock(mutex);
        ++calls;
        condition.notify_all();
        return ndk::ScopedAStatus::ok();
    }
    void waitFor(int expected) {
        std::unique_lock<std::mutex> lock(mutex);
        assert(condition.wait_for(lock, std::chrono::seconds(2),
                                  [&] { return calls >= expected; }));
    }
    int count() { std::lock_guard<std::mutex> lock(mutex); return calls; }
};
struct Session;
struct Device {
    int (*reset_lockout)(Device*, const hw_auth_token_t*);
    Session* session = nullptr;
    int result = 0;
    int requests = 0;
    int observedChallenge = 0;
    bool vendorLocked = true;
    bool synchronousCallback = false;
    bool synchronousError = false;
};
struct Session {
    explicit Session(Device* device = nullptr) : mDevice(device) {}
    Device* mDevice;
    LockoutTracker mLockoutTracker;
    bool mIsLockoutTimerStarted = false;
    bool mIsLockoutTimerAborted = false;
    std::shared_ptr<Callback> mCb = std::make_shared<Callback>();
    std::shared_ptr<std::atomic_bool> mLockoutResetCompletion;
    // SESSION_METHODS
};
static int resetVendor(Device* device, const hw_auth_token_t* hat) {
    ++device->requests;
    device->observedChallenge = hat->challenge;
    if (device->result == 0) device->vendorLocked = false;
    if (device->synchronousCallback) device->session->vendorReset();
    if (device->synchronousError) device->session->vendorError();
    return device->result;
}
static void assertCallbacks(const std::shared_ptr<Callback>& cb, int count) {
    if (count) cb->waitFor(count);
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    assert(cb->count() == count);
}
int main() {
    {
        Device device{resetVendor};
        Session session{&device};
        device.session = &session;
        assert(session.resetLockout({77}).isOk());
        assert(device.requests == 1 && device.observedChallenge == 77);
        assert(!device.vendorLocked);
        assertCallbacks(session.mCb, 1);
        std::cout << "PASS local kNone still validates HAT and resets vendor\n";
    }
    {
        Device device{resetVendor};
        device.result = -23;
        Session session{&device};
        device.session = &session;
        session.mIsLockoutTimerStarted = true;
        assert(session.resetLockout({}).error == -23);
        assert(device.requests == 1 && device.vendorLocked);
        assert(!session.mIsLockoutTimerAborted);
        assertCallbacks(session.mCb, 0);
        std::cout << "PASS rejected vendor reset has no success callback\n";
    }
    {
        Device device{resetVendor};
        device.synchronousCallback = true;
        Session session{&device};
        device.session = &session;
        assert(session.resetLockout({}).isOk());
        assertCallbacks(session.mCb, 1);
        std::cout << "PASS synchronous vendor callback completes once\n";
    }
    {
        Device device{resetVendor};
        Session session{&device};
        device.session = &session;
        assert(session.resetLockout({}).isOk());
        assertCallbacks(session.mCb, 1);
        session.vendorReset();
        session.vendorReset();
        assertCallbacks(session.mCb, 1);
        assert(session.resetLockout({}).isOk());
        assertCallbacks(session.mCb, 2);
        assert(device.requests == 2);
        std::cout << "PASS late duplicates suppressed; next reset gets a new token\n";
    }
    {
        Device device{resetVendor};
        Session session{&device};
        device.session = &session;
        session.mLockoutTracker.mode = LockoutTracker::LockoutMode::kPermanent;
        assert(session.resetLockout({}).isOk());
        assertCallbacks(session.mCb, 0);
        session.vendorReset();
        assertCallbacks(session.mCb, 1);
        std::cout << "PASS locally locked reset waits for vendor completion\n";
    }
    {
        Device device{resetVendor};
        device.synchronousError = true;
        Session session{&device};
        device.session = &session;
        assert(session.resetLockout({}).isOk());
        assertCallbacks(session.mCb, 0);
        std::cout << "PASS vendor error suppresses local completion\n";
    }
    {
        Device device{resetVendor};
        Session session{&device};
        auto token = std::make_shared<std::atomic_bool>(false);
        std::atomic_store(&session.mLockoutResetCompletion, token);
        session.invalidateLockoutReset();
        assert(token->load());
        assert(!std::atomic_load(&session.mLockoutResetCompletion));
        std::cout << "PASS operation/session change invalidates pending completion\n";
    }
    {
        Device device{resetVendor};
        auto session = std::make_unique<Session>();
        session->mDevice = &device;
        device.session = session.get();
        auto cb = session->mCb;
        assert(session->resetLockout({}).isOk());
        session.reset();
        assertCallbacks(cb, 1);
        std::cout << "PASS fallback owns callback after Session destruction\n";
    }
}
