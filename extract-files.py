#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: 2024 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

from os import path

import extract_utils.tools

from extract_utils.fixups_blob import (
    blob_fixup,
    blob_fixups_user_type,
)
from extract_utils.fixups_lib import (
    lib_fixup_remove,
    lib_fixups,
    lib_fixups_user_type,
)
from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)
from extract_utils.utils import run_cmd

CAMERA_STOCK_RUNPATH = '/vendor/lib64/camera-stock'
THERMAL_AES_KEY = 'thermalopenssl.h'.encode().hex()

CAMERA_STOCK_LIBRARIES = (
    'android.hardware.graphics.allocator-V2-ndk.so',
    'android.hardware.graphics.allocator@2.0.so',
    'android.hardware.graphics.allocator@3.0.so',
    'android.hardware.graphics.allocator@4.0.so',
    'android.hardware.graphics.common@1.0.so',
    'android.hardware.graphics.common@1.1.so',
    'android.hardware.graphics.common@1.2.so',
    'android.hardware.graphics.mapper@2.0.so',
    'android.hardware.graphics.mapper@2.1.so',
    'android.hardware.graphics.mapper@3.0.so',
    'android.hardware.graphics.mapper@4.0.so',
    'libcamera_metadata.so',
    'libcutils.so',
    'libdisplaydebug.so',
    'libdmabufheap.so',
    'libgralloc.qti.so',
    'libgralloccore.so',
    'libgralloctypes.so',
    'libgrallocutils.so',
    'libhardware.so',
    'libhidlbase.so',
    'libhidltransport.so',
    'libmapperutils.so',
    'libui.so',
    'libutils.so',
)

# OS3.0.6.0 camera blobs load allocator AIDL V1 at runtime alongside V2.
# Keep the stock V1 library as a copy rule, but omit it from Soong's link
# graph because Soong rejects two versions of one AIDL interface in a module.
lib_fixups: lib_fixups_user_type = {
    **lib_fixups,
    (
        'android.hardware.graphics.allocator-V1-ndk',
        'android.hardware.sensors-V2-ndk',
    ): lib_fixup_remove,
}


def set_camera_stock_runpath(ctx, file, file_path, *args, **kwargs):
    run_cmd(
        [
            extract_utils.tools.patchelf_version_path_map[
                extract_utils.tools.DEFAULT_PATCHELF_VERSION
            ],
            '--set-rpath',
            CAMERA_STOCK_RUNPATH,
            file_path,
        ]
    )


def camera_stock_executable_fixup():
    fixup = blob_fixup().call(
        set_camera_stock_runpath,
        need_tmp_dir=False,
    )

    for library in CAMERA_STOCK_LIBRARIES:
        fixup.add_needed(library)

    return fixup


def tune_thermal_charging(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    assert tmp_dir is not None

    decrypted_path = path.join(tmp_dir, 'thermal-normal.conf')
    cipher_args = [
        'openssl',
        'enc',
        '-aes-128-cbc',
        '-K',
        THERMAL_AES_KEY,
        '-iv',
        THERMAL_AES_KEY,
    ]

    run_cmd(cipher_args + ['-d', '-in', file_path, '-out', decrypted_path])

    with open(decrypted_path, encoding='utf-8') as thermal_file:
        config = thermal_file.read()

    # Only tune thermal_fcc_override (SIC-BAT). CPU/GPU clock limits and their
    # thermal thresholds remain identical to the stock regional configuration.
    replacements = {
        (
            'trig\t15000\t33000\t35500\t38500\t40500\t42000\t45500\t'
            '46000\t46500'
        ): (
            'trig\t15000\t33000\t38000\t39500\t41000\t42500\t44000\t'
            '45000\t46000\t46500'
        ),
        (
            'clr\t14000\t34000\t35200\t38000\t40000\t41700\t45000\t'
            '45500\t46000'
        ): (
            'clr\t14000\t34000\t37500\t39000\t40500\t42000\t43500\t'
            '44500\t45500\t46000'
        ),
        (
            'target\t0\t35000\t37300\t39500\t41500\t44000\t45500\t'
            '46000\t46500'
        ): (
            'target\t0\t35000\t41000\t42000\t43000\t44000\t44000\t'
            '45000\t46000\t46500'
        ),
        (
            'ks\t0\t0\t6650000\t6650000\t6650000\t6650000\t'
            '6650000\t6650000\t6650000'
        ): (
            'ks\t0\t0\t6650000\t6650000\t6650000\t6650000\t'
            '6650000\t6650000\t6650000\t6650000'
        ),
        (
            'ki\t0\t0\t100000\t100000\t100000\t100000\t100000\t'
            '100000\t100000'
        ): (
            'ki\t0\t0\t100000\t100000\t100000\t100000\t100000\t'
            '100000\t100000\t100000'
        ),
        (
            'kc\t0\t0\t800000\t500000\t500000\t500000\t500000\t'
            '500000\t500000'
        ): (
            'kc\t0\t0\t800000\t500000\t500000\t500000\t500000\t'
            '500000\t500000\t500000'
        ),
        (
            'max\t15600\t15600\t13500\t8000\t6000\t4500\t1000\t500\t'
            '300'
        ): (
            'max\t15600\t15600\t13500\t10000\t8000\t6000\t4000\t2000\t'
            '500\t300'
        ),
        (
            'min\t15600\t15600\t4500\t5000\t4000\t2500\t1000\t500\t'
            '300'
        ): (
            'min\t15600\t15600\t8000\t7000\t5000\t3500\t2500\t1200\t'
            '500\t300'
        ),
    }

    for old, new in replacements.items():
        if config.count(old) != 1:
            raise ValueError(f'Unexpected thermal charging contents: {old}')
        config = config.replace(old, new)

    with open(decrypted_path, 'w', encoding='utf-8', newline='') as thermal_file:
        thermal_file.write(config)

    run_cmd(cipher_args + ['-e', '-in', decrypted_path, '-out', file_path])


namespace_imports = [
    'device/xiaomi/sm8750-common',
    'hardware/qcom-caf/sm8750',
    'hardware/xiaomi',
    'vendor/qcom/opensource/commonsys-intf/display',
    'vendor/xiaomi/sm8750-common',
]

blob_fixups: blob_fixups_user_type = {
    (
        'odm/etc/thermal-gl-normal.conf',
        'odm/etc/thermal-ind-normal.conf',
        'odm/etc/thermal-normal.conf',
    ): blob_fixup().call(tune_thermal_charging),
    'odm/bin/hw/vendor.qti.camera.provider-service_64': camera_stock_executable_fixup(),
    # HyperOS suspends the face/QR AON pipelines before opening the full camera.
    # AOSP has no client for that handoff, so the pipelines retain SensorHw 1/2
    # and prevent Cinematic mode from reserving its reference-frame pipeline.
    # This is separate from SAT wide-always-on, which remains enabled below in
    # the stock configuration and is used for camera quality and lens switching.
    'odm/etc/camera/camxoverridesettings.txt': blob_fixup()
    # Xiaomi's super-night formatters route their destinations through a
    # compiler-generated sprintf helper. Convert the helpers to the ordinary
    # vsnprintf ABI. Preserve known destination sizes and use two bytes for the
    # one-character decrypt-dump formatter whose compiler object size is -1.
    # This keeps the complete decrypt and imaging paths while bounding their
    # diagnostic strings.
    #
    # MI_SN_Init copies a packed 64-byte initializer whose first compiler
    # object is only 22 bytes. __strncpy_chk2 treats that first object's bound
    # as the bound of the packed initializer and aborts before the copy. Keep
    # the original 64-byte copy (the following bytes contain fields consumed
    # by the parser) while routing it through the ordinary strncpy entry point.
    'odm/lib64/libmi_supernight_raw.so': blob_fixup()
        .sig_replace('18 78 08 94 F8 07 40 91', 'E4 78 08 94 F8 07 40 91')
        .sig_replace(
            'E8 03 02 AA E2 03 01 AA A4 43 01 D1 E1 03 1F 2A '
            'A9 83 1F F8 A9 83 00 91 AD B3 3E A9 E3 03 08 AA '
            'A9 AB 3D A9 60 05 40 AD A0 87 3D AD 38 79 08 94',
            '48 00 80 52 3F 00 00 F1 A3 43 01 D1 21 50 88 9A '
            'A9 83 1F F8 A9 83 00 91 AD B3 3E A9 1F 20 03 D5 '
            'A9 AB 3D A9 60 05 40 AD A0 87 3D AD 24 7A 08 94',
        )
        .sig_replace(
            'E8 03 02 AA E2 03 01 AA A4 43 01 D1 E1 03 1F 2A '
            'A9 83 1F F8 A9 83 00 91 AD B3 3E A9 E3 03 08 AA '
            'A9 AB 3D A9 60 05 40 AD A0 87 3D AD A4 76 08 94',
            '48 00 80 52 3F 00 00 F1 A3 43 01 D1 21 50 88 9A '
            'A9 83 1F F8 A9 83 00 91 AD B3 3E A9 1F 20 03 D5 '
            'A9 AB 3D A9 60 05 40 AD A0 87 3D AD 90 77 08 94',
        ),
    # alCFR_Run invalidates its instance when processing fails. Closing that
    # stale handle aborts in libmorpho_Depurple, while merely skipping cleanup
    # leaves Depurple stuck in its initialized state and degrades later frames.
    # Preserve the tuning allocation, mark the instance uninitialized, and let
    # the existing reference-count path recreate it on the next request.
    'odm/lib64/camera/plugins/com.xiaomi.plugin.depurple.so': blob_fixup()
        .sig_replace(
            'E0 03 13 AA 65 04 00 94 60 82 01 91 5D 04 00 94',
            'E0 03 13 AA 7F A2 00 B9 60 82 01 91 5D 04 00 94',
        ),
    'vendor/bin/hw/vendor.qti.hardware.display.allocator-service': camera_stock_executable_fixup(),
    (
        'odm/etc/camera/motiontuning.xml',
        'odm/etc/camera/snsc_bokeh_motiontuning.xml',
        'odm/etc/camera/snsc_enhance_motiontuning.xml',
        'odm/etc/camera/snsc_noface_motiontuning.xml',
        'odm/etc/camera/enhance_motiontuning.xml',
        'odm/etc/camera/snsc_motiontuning.xml'
    ): blob_fixup()
        .regex_replace('xml=version', 'xml version'),
    (
    'vendor/lib64/libcameraopt.so',
    ): blob_fixup().add_needed('libprocessgroup_shim.so'),
    (
        'odm/lib64/libMiEmojiEffect.so',
        'odm/lib64/libMiVideoFilter.so',
        'odm/lib64/libAncHumanPreviewBokeh.so',
        'odm/lib64/libTrueSight.so',
        'odm/lib64/libwa_widelens_undistort.so',
        'odm/lib64/libMiPhotoFilter.so'
    ): blob_fixup()
        .clear_symbol_version('AHardwareBuffer_allocate')
        .clear_symbol_version('AHardwareBuffer_describe')
        .clear_symbol_version('AHardwareBuffer_lockPlanes')
        .clear_symbol_version('AHardwareBuffer_release')
        .clear_symbol_version('AHardwareBuffer_unlock')
        .clear_symbol_version('AHardwareBuffer_lock')
        .clear_symbol_version('AHardwareBuffer_isSupported'),
    (
       'vendor/lib64/vendor.xiaomi.hardware.camera.injection-V1-ndk.so',
       'vendor/lib64/vendor.xiaomi.hardware.camera.injection-client.so',
       'vendor/lib64/vendor.xiaomi.hardware.camera.injection-service.so',
    ): blob_fixup()
        .replace_needed(
            'android.hardware.camera.device-V1-ndk.so',
            'android.hardware.camera.device-V2-ndk.so'
        ),
    (
        'vendor/lib64/libjpegdecoder_dada.so',
        'vendor/lib64/libjpegencoder_dada.so',
    ): blob_fixup()
        .fix_soname(),
    'vendor/lib64/libultrahdr_dada.so': blob_fixup()
        .replace_needed(
            'libjpegencoder.so',
            'libjpegencoder_dada.so'
        )
        .replace_needed(
            'libjpegdecoder.so',
            'libjpegdecoder_dada.so'
        )
        .fix_soname(),
    ('odm/lib64/camera/plugins/com.xiaomi.plugin.jpegrAggr.so', 'odm/lib64/camera/plugins/com.xiaomi.plugin.gainmap.so'): blob_fixup()
        .replace_needed(
            'libultrahdr.so',
            'libultrahdr_dada.so'
        ),
    (
        'vendor/lib64/libcamera2ndk_vendor.so',
    ): blob_fixup()
        .replace_needed('android.frameworks.cameraservice.device-V2-ndk.so', 'android.frameworks.cameraservice.device-V3-ndk.so')
        .replace_needed('android.frameworks.cameraservice.service-V2-ndk.so', 'android.frameworks.cameraservice.service-V3-ndk.so')
}

module = ExtractUtilsModule(
    'dada',
    'xiaomi',
    blob_fixups=blob_fixups,
    lib_fixups=lib_fixups,
    namespace_imports=namespace_imports,
    check_elf=True,
)

if __name__ == '__main__':
    utils = ExtractUtils.device_with_common(
        module, 'sm8750-common', module.vendor
    )
    utils.run()
