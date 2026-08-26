import { IconSearch } from "../icons";

export default function TopHeader({ crumb, title, onUpload }) {
  return (
    <header className="ce-topheader">
      <div className="ce-topheader-titles">
        <span className="ce-topheader-crumb">{crumb}</span>
        <span className="ce-topheader-title">{title}</span>
      </div>
      <div className="ce-topheader-actions">
        <div className="ce-search-box">
          <IconSearch size={15} />
          <span>Search calls, leads, quotes</span>
        </div>
        <button type="button" className="ce-btn" disabled title="Not available in Phase 0">
          Export digest
        </button>
        <button type="button" className="ce-btn ce-btn-primary" onClick={onUpload}>
          Upload a call
        </button>
      </div>
    </header>
  );
}
