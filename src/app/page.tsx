'use client';

import { Suspense, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { CampusScene } from '../components/CampusScene';
import { BuildingPanel } from '../components/BuildingPanel';
import { SearchPanel } from '../components/SearchPanel';
import { RoutePanel } from '../components/RoutePanel';
import { TourPanel } from '../components/TourPanel';
import { SunPanel } from '../components/SunPanel';
import { PerfOverlay } from '../components/PerfOverlay';
import { AboutDialog } from '../components/AboutDialog';
import { QualityControl } from '../components/QualityControl';
import { Drawer } from '../components/Drawer';
import { Loader } from '../components/Loader';
import { useCampusStore } from '../lib/store';

function DeepLinks() {
  const searchParams = useSearchParams();
  const setSelectedBuildingId = useCampusStore((s) => s.setSelectedBuildingId);
  const setInfoOpen = useCampusStore((s) => s.setInfoOpen);
  const setRoute = useCampusStore((s) => s.setRoute);

  useEffect(() => {
    const b = searchParams.get('b');
    const from = searchParams.get('from');
    const to = searchParams.get('to');
    if (b) {
      setSelectedBuildingId(b);
      setInfoOpen(true);
    }
    if (from && to) {
      setRoute({ fromId: from, toId: to });
    }
  }, [searchParams, setSelectedBuildingId, setInfoOpen, setRoute]);

  return null;
}

function Home() {
  const focus = useCampusStore((s) => s.focus);
  return (
    <div className="app">
      <Loader />
      {/* Exposed for e2e: proves a label/mesh click issued a camera focus request. */}
      <div className="viewport" data-focus-id={focus?.id ?? ''}>
        <CampusScene />
        <div className="top-right">
          <SunPanel />
        </div>
        <Drawer label="controls">
          <h1>IIT Ropar · 3D Campus</h1>
          <SearchPanel />
          <QualityControl />
        </Drawer>
        <div className="bottom-left">
          <BuildingPanel />
        </div>
        <div className="bottom-right">
          <RoutePanel />
          <TourPanel />
        </div>
        <PerfOverlay />
        <AboutDialog />
      </div>
      <DeepLinks />
    </div>
  );
}

export default function Page() {
  return (
    <Suspense fallback={null}>
      <Home />
    </Suspense>
  );
}
