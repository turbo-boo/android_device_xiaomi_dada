/*
 * Copyright (C) 2026 The LineageOS Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.lineageos.settings.memc;

import android.content.Context;
import android.os.SystemProperties;
import android.util.Log;

import androidx.preference.PreferenceManager;

/**
 * Video enhancement is a single mutually exclusive mode (off, memc, aie,
 * ais) expressed as a four-property truth table on the debug.media.video.*
 * properties. Exactly one mode is written at a time; off clears them all.
 */
public final class MemcUtils {

    private static final String TAG = "MemcUtils";

    /** The single preference key holding the selected mode. */
    public static final String KEY_MODE = "memc_mode";

    public static final String MODE_OFF = "off";
    public static final String MODE_MEMC = "memc";
    public static final String MODE_AIE = "aie";
    public static final String MODE_AIS = "ais";

    private static final String PROP_FRC = "debug.media.video.frc";
    private static final String PROP_VPP = "debug.media.video.vpp";
    private static final String PROP_VE = "debug.media.video.ve";
    private static final String PROP_AIS = "debug.media.video.ais";

    private static final boolean DEFAULT_ON = false;

    private MemcUtils() {}

    private static boolean isValidMode(String mode) {
        return MODE_OFF.equals(mode) || MODE_MEMC.equals(mode)
                || MODE_AIE.equals(mode) || MODE_AIS.equals(mode);
    }

    /**
     * The properties, not the stored preference, are what the media stack
     * acts on, so they are authoritative whenever they are available. A
     * combination that matches no valid mode reports off instead of
     * pretending a mode is active.
     */
    public static String getMode() {
        final boolean frc = SystemProperties.getBoolean(PROP_FRC, DEFAULT_ON);
        final boolean vpp = SystemProperties.getBoolean(PROP_VPP, DEFAULT_ON);
        final boolean ve = SystemProperties.getBoolean(PROP_VE, DEFAULT_ON);
        final boolean ais = SystemProperties.getBoolean(PROP_AIS, DEFAULT_ON);

        if (frc) {
            return !vpp && !ve && !ais ? MODE_MEMC : MODE_OFF;
        }
        if (vpp && ve && !ais) {
            return MODE_AIE;
        }
        if (vpp && !ve && ais) {
            return MODE_AIS;
        }
        return MODE_OFF;
    }

    /**
     * Write all four properties for exactly one mode (off clears every
     * property), then verify by reading them back. Returns false for an
     * invalid value, a write failure, or a mismatched readback; callers
     * must not persist the mode in that case.
     */
    public static boolean setMode(String mode) {
        if (!isValidMode(mode)) {
            return false;
        }
        final boolean frc = MODE_MEMC.equals(mode);
        final boolean vpp = MODE_AIE.equals(mode) || MODE_AIS.equals(mode);
        final boolean ve = MODE_AIE.equals(mode);
        final boolean ais = MODE_AIS.equals(mode);
        try {
            SystemProperties.set(PROP_FRC, toProp(frc));
            SystemProperties.set(PROP_VPP, toProp(vpp));
            SystemProperties.set(PROP_VE, toProp(ve));
            SystemProperties.set(PROP_AIS, toProp(ais));
        } catch (RuntimeException e) {
            Log.e(TAG, "Failed to set video enhancement mode " + mode, e);
            return false;
        }
        final String applied = getMode();
        if (!mode.equals(applied)) {
            Log.e(TAG, "Readback mismatch: requested " + mode + ", applied "
                    + applied);
            return false;
        }
        return true;
    }

    public static void persistMode(Context context, String mode) {
        if (!isValidMode(mode)) {
            return;
        }
        PreferenceManager.getDefaultSharedPreferences(context).edit()
                .putString(KEY_MODE, mode).apply();
    }

    /**
     * Restore the user's choice. The properties are volatile (they are not
     * persisted properties), while the stored mode survives reboots.
     */
    public static boolean apply(Context context) {
        final String saved = PreferenceManager
                .getDefaultSharedPreferences(context)
                .getString(KEY_MODE, MODE_OFF);
        return setMode(isValidMode(saved) ? saved : MODE_OFF);
    }

    private static String toProp(boolean value) {
        return value ? "true" : "false";
    }
}
