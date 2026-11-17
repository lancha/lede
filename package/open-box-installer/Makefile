include $(TOPDIR)/rules.mk

PKG_NAME:=open-box-installer
PKG_VERSION:=1
PKG_RELEASE:=1

include $(INCLUDE_DIR)/package.mk

define Package/open-box-installer
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=Official Open-Box installer
  DEPENDS:=+curl +ca-bundle
endef

define Package/open-box-installer/description
  Downloads the pinned official Open-Box installer on demand.
  The proprietary program itself is not redistributed in this firmware.
endef

define Build/Prepare
endef

define Build/Configure
endef

define Build/Compile
endef

define Package/open-box-installer/install
	$(INSTALL_DIR) $(1)/usr/sbin
	$(INSTALL_BIN) ./files/open-box-install $(1)/usr/sbin/open-box-install
endef

$(eval $(call BuildPackage,open-box-installer))