import {
  setDebug,
  themeParams,
  initData,
  viewport,
  init as initSDK,
  mockTelegramEnv,
  type ThemeParams,
  retrieveLaunchParams,
  emitEvent,
  miniApp,
  backButton,
  settingsButton,
  swipeBehavior,
} from "@tma.js/sdk-react";

export function init(options: {
  debug: boolean;
  eruda: boolean;
  mockForMacOS: boolean;
}): void {
  setDebug(options.debug);
  initSDK();

  options.eruda && void import("eruda").then(({ default: eruda }) => {
    eruda.init();
    eruda.position({ x: window.innerWidth - 50, y: 0 });
  });

  // Telegram for macOS doesn't respond to "web_app_request_theme" and sends an
  // incorrect payload for "web_app_request_safe_area", so both are mocked here.
  if (options.mockForMacOS) {
    let firstThemeSent = false;
    mockTelegramEnv({
      onEvent(event, next) {
        if (event.name === "web_app_request_theme") {
          let tp: ThemeParams = {};
          if (firstThemeSent) {
            tp = themeParams.state();
          } else {
            firstThemeSent = true;
            tp = retrieveLaunchParams().tgWebAppThemeParams;
          }
          return emitEvent("theme_changed", { theme_params: tp });
        }

        if (event.name === "web_app_request_safe_area") {
          return emitEvent("safe_area_changed", { left: 0, top: 0, right: 0, bottom: 0 });
        }

        next();
      },
    });
  }

  backButton.mount.ifAvailable();
  settingsButton.mount.ifAvailable();
  swipeBehavior.mount.ifAvailable();
  swipeBehavior.disableVertical.ifAvailable();
  initData.restore();

  if (miniApp.mount.isAvailable()) {
    themeParams.mount();
    miniApp.mount();
    themeParams.bindCssVars();
  }

  if (viewport.mount.isAvailable()) {
    void viewport.mount().then(() => {
      viewport.bindCssVars();
      if (viewport.expand.isAvailable()) {
        viewport.expand();
      }
    });
  }
}