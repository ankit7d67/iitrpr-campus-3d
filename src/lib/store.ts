import { create } from 'zustand';

export type Quality = 'auto' | 'low' | 'high';

export interface RouteSelection {
  fromId: string;
  toId: string;
}

export interface CampusState {
  quality: Quality;
  selectedBuildingId: string | null;
  searchQuery: string;
  route: RouteSelection | null;
  tourStopIndex: number;
  sunUtcMs: number;
  perfFps: number | null;
  infoOpen: boolean;
  aboutOpen: boolean;
  night: boolean;
  drawerOpen: boolean;
  /** Camera focus request: fly the camera to a building (BLDG_/ENTR_ id). seq
   *  increments so re-focusing the same building re-triggers the animation. */
  focus: { id: string; seq: number } | null;
  setQuality: (quality: Quality) => void;
  setSelectedBuildingId: (selectedBuildingId: string | null) => void;
  setSearchQuery: (searchQuery: string) => void;
  setRoute: (route: RouteSelection | null) => void;
  setTourStopIndex: (tourStopIndex: number) => void;
  setSunUtcMs: (sunUtcMs: number) => void;
  setPerfFps: (perfFps: number | null) => void;
  setInfoOpen: (infoOpen: boolean) => void;
  setAboutOpen: (aboutOpen: boolean) => void;
  setNight: (night: boolean) => void;
  setDrawerOpen: (drawerOpen: boolean) => void;
  toggleDrawer: () => void;
  focusOn: (id: string) => void;
}

export const useCampusStore = create<CampusState>()((set) => ({
  quality: 'auto',
  selectedBuildingId: null,
  searchQuery: '',
  route: null,
  tourStopIndex: 0,
  sunUtcMs: Date.now(),
  perfFps: null,
  infoOpen: false,
  aboutOpen: false,
  night: false,
  drawerOpen: true,
  focus: null,
  setQuality: (quality) => set({ quality }),
  setSelectedBuildingId: (selectedBuildingId) => set({ selectedBuildingId }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setRoute: (route) => set({ route }),
  setTourStopIndex: (tourStopIndex) => set({ tourStopIndex }),
  setSunUtcMs: (sunUtcMs) => set({ sunUtcMs }),
  setPerfFps: (perfFps) => set({ perfFps }),
  setInfoOpen: (infoOpen) => set({ infoOpen }),
  setAboutOpen: (aboutOpen) => set({ aboutOpen }),
  setNight: (night) => set({ night }),
  setDrawerOpen: (drawerOpen) => set({ drawerOpen }),
  toggleDrawer: () => set((s) => ({ drawerOpen: !s.drawerOpen })),
  focusOn: (id) => set((s) => ({ focus: { id, seq: (s.focus?.seq ?? 0) + 1 } })),
}));
