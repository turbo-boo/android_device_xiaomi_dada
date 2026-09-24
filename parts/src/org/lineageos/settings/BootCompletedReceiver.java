/*
 * Copyright (C) 2015 The CyanogenMod Project
 *               2017-2020 The LineageOS Project
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

package org.lineageos.settings;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.util.Log;
import android.content.SharedPreferences;
import androidx.preference.PreferenceManager;

import org.lineageos.settings.doze.PocketService;
import org.lineageos.settings.cloudmode.CloudModeUtils;
import org.lineageos.settings.dcdimming.DcDimmingUtils;
import org.lineageos.settings.edgefilter.EdgeFilterUtils;
import org.lineageos.settings.memc.MemcUtils;
import org.lineageos.settings.thermal.ThermalUtils;
import org.lineageos.settings.refreshrate.RefreshUtils;

public class BootCompletedReceiver extends BroadcastReceiver {
    private static final boolean DEBUG = false;
    private static final String TAG = "XiaomiParts";
    private static final String DC_DIMMING_KEY = "dc_dimming";

    @Override
    public void onReceive(final Context context, Intent intent) {
        SharedPreferences sharedPrefs = PreferenceManager.getDefaultSharedPreferences(context);
        if (DEBUG)
            Log.d(TAG, "Received boot completed intent");
        ThermalUtils.startService(context);
        RefreshUtils.startService(context);

        // Pocket
        PocketService.startService(context);

        // DC Dimming
        boolean dcDimmingEnabled = sharedPrefs.getBoolean(DC_DIMMING_KEY, false);
        DcDimmingUtils.setEnabled(dcDimmingEnabled);

        // Video enhancement mode (off/memc/aie/ais). The properties do not
        // survive a reboot, and writing them has no service dependency, so no
        // retry loop.
        MemcUtils.apply(context);

        // Edge mis-touch protection
        EdgeFilterUtils.applyLater(context);

        // Wet touch and glove cloud modes
        CloudModeUtils.applyLater(context);
    }
}
