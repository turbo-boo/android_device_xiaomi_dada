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

import android.os.Bundle;

import androidx.preference.ListPreference;
import androidx.preference.Preference;
import androidx.preference.Preference.OnPreferenceChangeListener;

import com.android.settingslib.widget.SettingsBasePreferenceFragment;

import org.lineageos.settings.R;

public class MemcSettingsFragment extends SettingsBasePreferenceFragment implements
        OnPreferenceChangeListener {

    private ListPreference mModePreference;

    @Override
    public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {
        setPreferencesFromResource(R.xml.memc_settings, rootKey);

        mModePreference = findPreference(MemcUtils.KEY_MODE);
        mModePreference.setOnPreferenceChangeListener(this);
    }

    @Override
    public void onResume() {
        super.onResume();
        // Reflect the properties, which is what the media stack acts on,
        // without touching the stored choice: the properties are volatile and
        // may have been reset by a reboot or changed underneath us. The
        // preference is non-persistent, so this only updates the display.
        mModePreference.setValue(MemcUtils.getMode());
    }

    @Override
    public boolean onPreferenceChange(Preference preference, Object newValue) {
        if (!MemcUtils.KEY_MODE.equals(preference.getKey())) {
            return true;
        }
        final String mode = (String) newValue;
        // Apply first; setMode rejects invalid values and verifies the
        // properties by reading them back.
        if (!MemcUtils.setMode(mode)) {
            // Roll the selection back to the actual property state.
            mModePreference.setValue(MemcUtils.getMode());
            return false;
        }
        MemcUtils.persistMode(getContext(), mode);
        return true;
    }
}
