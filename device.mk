#
# Copyright (C) 2024 The LineageOS Project
#
# SPDX-License-Identifier: Apache-2.0
#

# Use the allocator built with the same private ABI as the stock camera stack.
TARGET_USES_PREBUILT_DISPLAY_ALLOCATOR := true

# Inherit from sm8750-common
$(call inherit-product, device/xiaomi/sm8750-common/common.mk)

# Get non-open-source specific aspects
$(call inherit-product, vendor/xiaomi/dada/dada-vendor.mk)

# MIUI Camera
$(call inherit-product, device/xiaomi/dada-miuicamera/device.mk)

# Device-specific settings
PRODUCT_PACKAGES += \
    XiaomiParts

# Android Virtualization Framework
# Stock pvmfw cannot verify the AVF remote-attestation Service VM shipped by
# the platform. Keep AVF enabled, but do not attempt unsupported AVF RKP.
PRODUCT_SYSTEM_PROPERTIES += \
    avf.remote_attestation.enabled=false

# The stock camera HAL directly loads the frozen sensors AIDL V2 while the
# platform sensorservice uses V3.
PRODUCT_PACKAGES += \
    android.hardware.sensors-V2-ndk

# Overlays
PRODUCT_PACKAGES += \
    ApertureResDada \
    FrameworksResDada \
    FrameworksResDadaEsim \
    SettingsOverlayDada \
    SystemUIResDada

# eSIM
PRODUCT_PACKAGES += \
    XiaomiEsimSwitcher

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.telephony.euicc.mep.xml:$(TARGET_COPY_OUT_PRODUCT)/etc/permissions/android.hardware.telephony.euicc.mep.xml \
    $(LOCAL_PATH)/configs/permissions/privapp-permissions-EuiccGoogle.xml:$(TARGET_COPY_OUT_PRODUCT)/etc/permissions/privapp-permissions-EuiccGoogle.xml

# Soong namespaces
PRODUCT_SOONG_NAMESPACES += \
    $(LOCAL_PATH)

# BCR
$(call inherit-product, vendor/bcr/bcr.mk)
