include $(TOPDIR)/rules.mk

PKG_NAME:=lede-default-settings
PKG_VERSION:=1
PKG_RELEASE:=1

include $(INCLUDE_DIR)/package.mk

define Package/lede-default-settings
  SECTION:=base
  CATEGORY:=Base system
  TITLE:=Family LEDE initial network and UI defaults
  DEPENDS:=+luci-base
endef

define Build/Prepare
endef

define Build/Configure
endef

define Build/Compile
endef

define Package/lede-default-settings/install
	$(INSTALL_DIR) $(1)/etc/uci-defaults
	$(INSTALL_BIN) ./files/99-lede-family-defaults $(1)/etc/uci-defaults/
endef

$(eval $(call BuildPackage,lede-default-settings))
