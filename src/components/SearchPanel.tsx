'use client';

import { useEffect, useState } from 'react';
import { useCampus } from '../lib/data';
import { searchBuildings } from '../lib/search';
import { useCampusStore } from '../lib/store';

export function SearchPanel() {
  const { campus } = useCampus();
  const query = useCampusStore((s) => s.searchQuery);
  const setQuery = useCampusStore((s) => s.setSearchQuery);
  const setSelectedBuildingId = useCampusStore((s) => s.setSelectedBuildingId);
  const setInfoOpen = useCampusStore((s) => s.setInfoOpen);
  const [input, setInput] = useState(query);

  useEffect(() => {
    setInput(query);
  }, [query]);

  const buildings = campus?.buildings ?? [];
  const results = searchBuildings(buildings, query).slice(0, 12);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (results.length > 0) {
      setSelectedBuildingId(results[0].id);
      setInfoOpen(true);
    }
  };

  return (
    <div className="search-panel">
      <form onSubmit={onSubmit} className="search-form">
        <input
          type="search"
          value={input}
          placeholder="Search buildings, hostels, departments…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') setQuery(input);
          }}
          aria-label="Search campus"
        />
        <button type="submit">Go</button>
      </form>
      {query.trim().length > 0 && campus && (
        <ul className="search-results" role="listbox">
          {results.map((b) => (
            <li key={b.id}>
              <button
                type="button"
                onClick={() => {
                  setSelectedBuildingId(b.id);
                  setInfoOpen(true);
                }}
              >
                <strong>{b.name}</strong>
                <span>{b.category}</span>
              </button>
            </li>
          ))}
          {results.length === 0 && <li className="empty">No matches. Try “hostel”, “library”.</li>}
        </ul>
      )}
    </div>
  );
}
