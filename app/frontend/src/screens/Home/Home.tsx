import { Callout } from "@/components/Callout";
import { Field } from "@/components/Field";
import { FloatingTabs } from "@/components/FloatingTabs";
import { Icon } from "@/components/Icon/Icon";
import { RoundToggle } from "@/components/RoundToggle";
import { TabPager } from "@/components/TabPager";
import { TelegramLoginButton } from "@/components/TelegramLoginButton";
import { countActiveFilters, selectCatalog } from "@/data/query";
import { hydrateFromServer, setAlertsEnabled, toggleBell, toggleFavorite } from "@/data/sync";
import type { Provider } from "@/data/types";
import type { ReactNode } from "react";
import { useT } from "@/i18n";
import { cx } from "@/lib/cx";
import { reducedMotion } from "@/lib/motion";
import { notify } from "@/lib/telegram";
import { isHydrated, onHydrated } from "@/lib/storage";
import { useAlerts } from "@/stores/alerts";
import { useAuth } from "@/stores/auth";
import { useCatalog } from "@/stores/catalog";
import { PAGE_SIZE, type Tab, useCatalogQuery } from "@/stores/catalogQuery";
import { useFavorites } from "@/stores/favorites";
import { useNames } from "@/stores/names";
import { useSubscriptions } from "@/stores/subscriptions";
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./Home.module.css";
import { ProviderPane } from "./ProviderPane";
import { TonLogo } from "./TonLogo";

const RELOAD_SPIN_MS = 1100;
const SCROLL_TOP_THRESHOLD = 360;
const PENDING_ROWS = 4;
const TABS = ["subs", "list", "fav"] as const;

export function Home() {
  const t = useT();
  const navigate = useNavigate();

  const providers = useCatalog((s) => s.providers);
  const bounds = useCatalog((s) => s.bounds);
  const status = useCatalog((s) => s.status);
  const errorStatus = useCatalog((s) => s.errorStatus);
  const load = useCatalog((s) => s.load);
  const reload = useCatalog((s) => s.reload);

  const tab = useCatalogQuery((s) => s.tab);
  const search = useCatalogQuery((s) => s.search);
  const sort = useCatalogQuery((s) => s.sort);
  const filters = useCatalogQuery((s) => s.filters);
  const visible = useCatalogQuery((s) => s.visible);
  const setTab = useCatalogQuery((s) => s.setTab);
  const setSearch = useCatalogQuery((s) => s.setSearch);
  const setSortField = useCatalogQuery((s) => s.setSortField);
  const loadMore = useCatalogQuery((s) => s.loadMore);
  const resetFilters = useCatalogQuery((s) => s.resetFilters);

  const favorites = useFavorites((s) => s.favorites);
  const names = useNames((s) => s.providers);
  const loggedIn = useAuth((s) => s.loggedIn);
  const subscribed = useSubscriptions((s) => s.subscribed);
  const alertsOff = useSubscriptions((s) => s.alertsOff);
  const alertEnabled = useAlerts((s) => s.enabled);

  const panes = useRef<Record<string, HTMLDivElement | null>>({});
  const reloadTimer = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => () => clearTimeout(reloadTimer.current), []);
  const [progress, setProgress] = useState(TABS.indexOf(tab));
  const [showTop, setShowTop] = useState(false);
  const scrubRef = useRef<(position: number | null) => void>(() => {});
  const [spinning, setSpinning] = useState(false);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setShowTop((panes.current[tab]?.scrollTop ?? 0) > SCROLL_TOP_THRESHOLD);
  }, [tab]);

  const listItems = useMemo(
    () => selectCatalog(providers, { favTab: false, search, filters, sort, favorites, names, bounds }),
    [providers, search, filters, sort, favorites, names, bounds],
  );
  const favItems = useMemo(
    () => selectCatalog(providers, { favTab: true, search, filters, sort, favorites, names, bounds }),
    [providers, search, filters, sort, favorites, names, bounds],
  );
  const subItems = useMemo(() => {
    if (!loggedIn) return [];
    const query = search.trim().toLowerCase();
    return providers.filter(
      (p) =>
        subscribed.includes(p.pubkey) &&
        (!query ||
          p.pubkey.toLowerCase().includes(query) ||
          (names[p.pubkey] ?? "").toLowerCase().includes(query)),
    );
  }, [loggedIn, providers, subscribed, search, names]);

  const hydrated = useSyncExternalStore(onHydrated, isHydrated);
  const activeFilters = countActiveFilters(filters);
  const initialLoading = status !== "ready" && status !== "error";
  const loading = spinning || initialLoading;
  const subsLoading = !hydrated || (loggedIn && loading && subscribed.length > 0);
  const favLoading = !hydrated || (loading && favorites.length > 0);
  const isError = status === "error" && providers.length === 0;

  const onReload = () => {
    if (spinning) return;
    setSpinning(true);
    const startedAt = performance.now();
    void reload()
      .then((ok) => {
        if (!ok) notify("error");
      })
      .finally(() => {
        const rest = Math.max(0, RELOAD_SPIN_MS - (performance.now() - startedAt));
        reloadTimer.current = setTimeout(() => setSpinning(false), rest);
      });
    if (useAuth.getState().token) {
      hydrateFromServer().catch((error: unknown) => console.error("reload sync failed", error));
    }
  };

  const onPaneScroll = (paneTab: Tab, scrollTop: number) => {
    if (paneTab === tab) setShowTop(scrollTop > SCROLL_TOP_THRESHOLD);
  };

  const scrollToTop = () => {
    panes.current[tab]?.scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" });
    setShowTop(false);
  };

  const openProvider = (pubkey: string) => navigate(`/provider/${pubkey}`);

  const starToggle = (provider: Provider) => (
    <RoundToggle
      glyph="star"
      size={18}
      active={favorites.includes(provider.pubkey)}
      ariaLabel={t.fav}
      onClick={(event) => {
        event.stopPropagation();
        toggleFavorite(provider.pubkey);
      }}
    />
  );

  const bellToggle = (provider: Provider) => (
    <RoundToggle
      glyph="bell"
      size={17}
      active={!alertsOff.includes(provider.pubkey)}
      ariaLabel={t.notifBtn}
      onClick={(event) => {
        event.stopPropagation();
        toggleBell(provider.pubkey);
      }}
    />
  );

  const listHero = <Callout hero icon={<TonLogo />} title={t.mainTitle} desc={t.mainDesc} />;

  const subsHero = <Callout hero glyph="bell" title={t.subsTitle} desc={t.subsDesc} />;

  const favHero = <Callout hero glyph="star" title={t.favTitle} desc={t.favDesc} />;

  const sortToolbar = (
    <div className={styles.toolbar}>
      <button type="button" className={styles.toolbarBtn} onClick={() => setSortField(sort.field)}>
        <span className={cx(styles.sortChevron, sort.dir === "asc" && styles.sortChevronUp)}>
          <Icon glyph="chevronDown" size={13} color="var(--ts-accent)" />
        </span>
        {t.sortField[sort.field]}
      </button>
      <button type="button" className={styles.toolbarBtn} onClick={() => navigate("/filters")}>
        <Icon glyph="sliders" size={16} />
        {t.filters}
        {activeFilters > 0 && <span className={styles.filterDot} />}
      </button>
    </div>
  );

  const listToolbar = (listItems.length > 0 || loading) && sortToolbar;

  const favToolbar = (favItems.length > 0 || favLoading) && sortToolbar;

  const subsToolbar = (subItems.length > 0 || subsLoading) && (
    <div className={styles.toolbar}>
      <button type="button" className={styles.toolbarBtn} onClick={() => setAlertsEnabled(!alertEnabled)}>
        {alertEnabled ? (
          <Icon glyph="bell" size={16} color="var(--ts-accent)" filled />
        ) : (
          <Icon glyph="bellOff" size={16} color="var(--ts-hint)" />
        )}
        {t.notifBtn}
      </button>
      <button type="button" className={styles.toolbarBtn} onClick={() => navigate("/alerts")}>
        <Icon glyph="sliders" size={16} />
        {t.settingsBtn}
      </button>
    </div>
  );

  const query = search.trim();

  const marks = {
    subs: { glyph: "bell" as const, title: t.subsTitle },
    list: { icon: <TonLogo />, title: t.mainTitle },
    fav: { glyph: "star" as const, title: t.favTitle },
  };

  const actionButton = (label: string, onClick: () => void) => (
    <button type="button" className={styles.calloutBtn} onClick={onClick}>
      {label}
    </button>
  );

  const state = (key: Tab, desc: ReactNode, action?: ReactNode) => (
    <Callout hero {...marks[key]} desc={desc}>
      {action}
    </Callout>
  );

  const errorState = (key: Tab) =>
    state(key, errorStatus !== null ? `${t.loadError} (HTTP ${errorStatus})` : t.loadError, actionButton(t.retry, onReload));

  const searchState = (key: Tab) =>
    state(key, t.searchEmpty, listItems.length > 0 ? actionButton(t.searchInCatalog(listItems.length), () => setTab("list")) : undefined);

  const pane = (key: Tab) => {
    if (key === "subs") {
      const rows = subItems.slice(0, visible.subs);
      return (
        <ProviderPane
          hero={subItems.length > 0 || subsLoading ? subsHero : undefined}
          toolbar={subsToolbar}
          count={loggedIn && subItems.length > 0 ? t.showing(rows.length, subItems.length) : null}
          loading={subsLoading}
          skeletonCount={rows.length || (hydrated ? Math.min(subscribed.length, PAGE_SIZE) : PENDING_ROWS)}
          rows={rows}
          trailing={bellToggle}
          fallback={
            !loggedIn ? (
              state("subs", t.loginNeeded, <TelegramLoginButton />)
            ) : isError ? (
              errorState("subs")
            ) : query ? (
              searchState("subs")
            ) : (
              state("subs", t.subsEmpty, actionButton(t.findProviders, () => setTab("list")))
            )
          }
          onOpen={openProvider}
          onLoadMore={subItems.length > rows.length ? () => loadMore("subs") : undefined}
        />
      );
    }

    const items = key === "fav" ? favItems : listItems;
    const rows = items.slice(0, visible[key]);
    return (
      <ProviderPane
        hero={items.length > 0 || (key === "fav" ? favLoading : loading) ? (key === "fav" ? favHero : listHero) : undefined}
        toolbar={key === "fav" ? favToolbar : listToolbar}
        count={items.length > 0 ? t.showing(rows.length, items.length) : null}
        loading={key === "fav" ? favLoading : loading}
        skeletonCount={
          rows.length || (key === "fav" ? (hydrated ? Math.min(favorites.length, PAGE_SIZE) : PENDING_ROWS) : PAGE_SIZE)
        }
        rows={rows}
        trailing={starToggle}
        fallback={
          isError ? (
            errorState(key)
          ) : query ? (
            searchState(key)
          ) : key === "fav" && favorites.length === 0 ? (
            state("fav", t.favEmpty, actionButton(t.findProviders, () => setTab("list")))
          ) : (
            state(key, t.providersNotFound, activeFilters > 0 ? actionButton(t.reset, resetFilters) : undefined)
          )
        }
        onOpen={openProvider}
        onLoadMore={items.length > rows.length ? () => loadMore(key) : undefined}
      />
    );
  };

  return (
    <div className={styles.screen}>
      <nav className={styles.nav}>
        <Field
          glyph="search"
          value={search}
          onChange={setSearch}
          placeholder={tab === "subs" ? t.searchSubs : tab === "fav" ? t.searchFav : t.searchPlaceholder}
          trailing={
            search && (
              <button type="button" aria-label="Clear" className={styles.searchClear} onClick={() => setSearch("")}>
                <Icon glyph="close" size={16} color="var(--ts-hint)" stroke={2} />
              </button>
            )
          }
        />
        <div className={styles.navActions}>
          <button type="button" aria-label="Refresh" className={styles.headerBtn} onClick={onReload}>
            <span className={spinning ? styles.spin : undefined}>
              <Icon glyph="reload" size={20} color="var(--ts-hint)" />
            </span>
          </button>
          <button type="button" aria-label={t.settings} className={styles.headerBtn} onClick={() => navigate("/menu")}>
            <Icon glyph="menu" size={22} color="var(--ts-hint)" />
          </button>
        </div>
      </nav>

      <TabPager
        tabs={TABS}
        tab={tab}
        scrubRef={scrubRef}
        panes={panes}
        onTabChange={setTab}
        onProgress={setProgress}
        onPaneScroll={onPaneScroll}
      >
        {pane}
      </TabPager>

      <button
        type="button"
        aria-label="Scroll to top"
        aria-hidden={!showTop}
        tabIndex={showTop ? 0 : -1}
        className={cx(styles.fab, showTop && styles.fabVisible)}
        onClick={scrollToTop}
      >
        <Icon glyph="arrowUp" size={22} color="#fff" />
      </button>

      <FloatingTabs
        tabs={[
          { key: "subs", label: t.subs, glyph: "bell" },
          { key: "list", label: t.list, icon: (active) => <TonLogo size={22} mono filled={active} /> },
          { key: "fav", label: t.fav, glyph: "star" },
        ]}
        tab={tab}
        progress={progress}
        onSelect={setTab}
        onScrub={(position) => scrubRef.current(position)}
      />

    </div>
  );
}
