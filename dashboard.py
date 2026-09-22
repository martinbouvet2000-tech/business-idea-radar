#!/usr/bin/env python3
"""Reddit Idea Radar — Military-Grade Dashboard"""

import json
import sys
import os
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

# Config via environment so the same file works locally and in a container.
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(Path.home() / "idea-radar-output")))
PORT = int(os.getenv("PORT", "8421"))
HOST = os.getenv("HOST", "127.0.0.1")

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IDEA RADAR</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --bg: #050508;
  --surface: #0c0c14;
  --surface2: #13131f;
  --surface3: #1a1a2a;
  --border: #1e1e30;
  --border2: #2a2a40;
  --text: #e4e4f0;
  --text2: #7878a0;
  --text3: #4a4a6a;
  --accent: #6366f1;
  --accent2: #818cf8;
  --green: #10b981;
  --green2: #34d399;
  --orange: #f59e0b;
  --red: #ef4444;
  --cyan: #06b6d4;
  --purple: #a855f7;
  --pink: #ec4899;
  --glow-accent: rgba(99,102,241,0.15);
  --glow-green: rgba(16,185,129,0.12);
  --tier1: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  --tier2: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
}
body {
  font-family: 'Inter', -apple-system, system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  min-height: 100vh;
  overflow-x: hidden;
}

/* Scan line effect */
body::after {
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 9999;
  background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px);
}

.container { max-width: 1520px; margin: 0 auto; padding: 1.5rem 2rem; }

/* ── HEADER ── */
header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1rem 0 1.5rem; border-bottom: 1px solid var(--border);
  margin-bottom: 1.5rem;
}
.brand { display: flex; align-items: center; gap: 1rem; }
.brand-icon {
  width: 48px; height: 48px; border-radius: 12px;
  background: var(--tier1); display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem; box-shadow: 0 0 20px var(--glow-accent);
}
.brand h1 {
  font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; font-weight: 800;
  letter-spacing: 0.08em; text-transform: uppercase;
}
.brand h1 span { background: var(--tier1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.brand .sub { font-size: 0.7rem; color: var(--text3); font-family: 'JetBrains Mono', monospace; letter-spacing: 0.15em; text-transform: uppercase; }

.header-controls { display: flex; gap: 0.75rem; align-items: center; }
.file-select select {
  background: var(--surface2); border: 1px solid var(--border); color: var(--text);
  padding: 0.55rem 1rem; border-radius: 8px; font-size: 0.8rem;
  font-family: 'JetBrains Mono', monospace;
}
.run-btn {
  background: var(--tier1); border: none; color: white; padding: 0.6rem 1.4rem;
  border-radius: 8px; cursor: pointer; font-weight: 700; font-size: 0.8rem;
  font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em;
  text-transform: uppercase; transition: all 0.3s; position: relative; overflow: hidden;
}
.run-btn:hover { box-shadow: 0 0 25px var(--glow-accent); transform: translateY(-1px); }
.run-btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; box-shadow: none; }
.run-btn.scanning { animation: pulse-btn 1.5s infinite; }
@keyframes pulse-btn { 0%,100% { box-shadow: 0 0 10px var(--glow-accent); } 50% { box-shadow: 0 0 30px var(--glow-accent); } }

/* ── COMMAND BAR (search + filters) ── */
.command-bar {
  display: flex; gap: 0.75rem; margin-bottom: 1.5rem; flex-wrap: wrap; align-items: center;
}
.search-box {
  flex: 1; min-width: 250px; position: relative;
}
.search-box input {
  width: 100%; background: var(--surface); border: 1px solid var(--border);
  color: var(--text); padding: 0.65rem 1rem 0.65rem 2.5rem; border-radius: 10px;
  font-size: 0.85rem; transition: border-color 0.2s;
  font-family: 'JetBrains Mono', monospace;
}
.search-box input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 15px var(--glow-accent); }
.search-box input::placeholder { color: var(--text3); }
.search-box::before {
  content: '⚲'; position: absolute; left: 0.85rem; top: 50%; transform: translateY(-50%);
  color: var(--text3); font-size: 1rem;
}
.filter-btn {
  padding: 0.55rem 1rem; border-radius: 8px; border: 1px solid var(--border);
  background: var(--surface); color: var(--text2); cursor: pointer;
  font-size: 0.78rem; transition: all 0.25s; font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.03em; text-transform: uppercase;
}
.filter-btn:hover { border-color: var(--accent); color: var(--text); }
.filter-btn.active { background: var(--accent); border-color: var(--accent); color: white; box-shadow: 0 0 15px var(--glow-accent); }
.sort-select {
  background: var(--surface); border: 1px solid var(--border); color: var(--text2);
  padding: 0.55rem 0.8rem; border-radius: 8px; font-size: 0.78rem;
  font-family: 'JetBrains Mono', monospace;
}

/* ── STATS GRID ── */
.stats-grid {
  display: grid; grid-template-columns: repeat(6, 1fr);
  gap: 0.75rem; margin-bottom: 1.5rem;
}
.stat-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 1rem 1.2rem; position: relative; overflow: hidden;
}
.stat-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  opacity: 0.6;
}
.stat-card.total::before { background: linear-gradient(90deg, var(--accent), var(--purple)); }
.stat-card.t1::before { background: var(--tier1); }
.stat-card.t2::before { background: var(--tier2); }
.stat-card.score::before { background: linear-gradient(90deg, var(--green), var(--green2)); }
.stat-card.avg::before { background: linear-gradient(90deg, var(--orange), #fbbf24); }
.stat-card.subs::before { background: linear-gradient(90deg, var(--pink), var(--purple)); }
.stat-label { font-size: 0.65rem; text-transform: uppercase; color: var(--text3); letter-spacing: 0.1em; font-family: 'JetBrains Mono', monospace; }
.stat-value { font-size: 1.8rem; font-weight: 800; margin-top: 0.2rem; font-family: 'JetBrains Mono', monospace; }
.stat-value.c-accent { color: var(--accent2); }
.stat-value.c-t1 { color: var(--purple); }
.stat-value.c-t2 { color: var(--cyan); }
.stat-value.c-green { color: var(--green2); }
.stat-value.c-orange { color: var(--orange); }
.stat-value.c-pink { color: var(--pink); }
.stat-detail { font-size: 0.7rem; color: var(--text3); margin-top: 0.15rem; font-family: 'JetBrains Mono', monospace; }

/* ── MAIN LAYOUT (grid + sidebar) ── */
.main-layout {
  display: grid; grid-template-columns: 1fr 320px; gap: 1.5rem;
}

/* ── CARDS GRID ── */
.ideas-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 1rem;
}
.idea-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 1.3rem; transition: all 0.3s;
  cursor: pointer; position: relative; overflow: hidden;
}
.idea-card:hover {
  border-color: var(--accent); transform: translateY(-3px);
  box-shadow: 0 12px 40px rgba(99,102,241,0.08);
}
.idea-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
}
.idea-card.tier-1::before { background: var(--tier1); }
.idea-card.tier-2::before { background: var(--tier2); }
.idea-card.tier-1:hover { box-shadow: 0 12px 40px rgba(168,85,247,0.1); }
.idea-card.tier-2:hover { box-shadow: 0 12px 40px rgba(6,182,212,0.1); }

/* Rank badge */
.rank-badge {
  position: absolute; top: 0.8rem; right: 0.8rem;
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 800;
  background: var(--surface2); color: var(--text3); border: 1px solid var(--border);
}
.rank-badge.top3 { background: linear-gradient(135deg,#6366f1,#a855f7); color: white; border: none; box-shadow: 0 0 12px var(--glow-accent); }

.idea-header { display: flex; align-items: flex-start; gap: 0.8rem; margin-bottom: 0.6rem; padding-right: 2.5rem; }
.idea-title { font-size: 0.95rem; font-weight: 700; line-height: 1.35; flex: 1; }
.idea-composite {
  font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; font-weight: 800;
  min-width: 48px; text-align: right; line-height: 1;
}
.idea-composite.high { color: var(--green2); }
.idea-composite.mid { color: var(--orange); }

.idea-meta { display: flex; gap: 0.5rem; margin-bottom: 0.6rem; flex-wrap: wrap; align-items: center; }
.tag {
  font-size: 0.65rem; padding: 0.15rem 0.5rem; border-radius: 4px;
  font-family: 'JetBrains Mono', monospace; letter-spacing: 0.04em; text-transform: uppercase;
}
.tag.tier-1 { background: rgba(168,85,247,0.12); color: var(--purple); border: 1px solid rgba(168,85,247,0.2); }
.tag.tier-2 { background: rgba(6,182,212,0.12); color: var(--cyan); border: 1px solid rgba(6,182,212,0.2); }
.tag.sub { background: var(--surface2); color: var(--text3); border: 1px solid var(--border); }
.tag.thread-heat { background: rgba(239,68,68,0.1); color: var(--red); border: 1px solid rgba(239,68,68,0.15); }

.idea-desc {
  font-size: 0.82rem; color: var(--text2); margin-bottom: 0.8rem;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}

/* Radar mini chart */
.radar-mini {
  width: 100%; height: 90px; margin-bottom: 0.5rem;
}

.idea-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 0.6rem; border-top: 1px solid var(--border);
  font-size: 0.72rem; color: var(--text3);
}
.idea-footer a { color: var(--accent2); text-decoration: none; font-family: 'JetBrains Mono', monospace; }
.idea-footer a:hover { text-decoration: underline; }
.thread-stats { display: flex; gap: 0.8rem; }
.thread-stats span { display: flex; align-items: center; gap: 0.25rem; }

/* ── SIDEBAR ── */
.sidebar { display: flex; flex-direction: column; gap: 1rem; }
.sidebar-panel {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 1.2rem; position: relative; overflow: hidden;
}
.sidebar-panel::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: var(--tier1); opacity: 0.5;
}
.sidebar-title {
  font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.1em; color: var(--text3);
  margin-bottom: 0.8rem;
}

/* Distribution chart */
.distrib-bar {
  display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;
}
.distrib-label { font-size: 0.72rem; color: var(--text2); width: 30px; text-align: right; font-family: 'JetBrains Mono', monospace; }
.distrib-track { flex: 1; height: 6px; background: var(--surface3); border-radius: 3px; overflow: hidden; }
.distrib-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.distrib-count { font-size: 0.65rem; color: var(--text3); width: 20px; font-family: 'JetBrains Mono', monospace; }

/* Subreddit breakdown */
.sub-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.4rem 0; border-bottom: 1px solid var(--border);
}
.sub-row:last-child { border-bottom: none; }
.sub-name { font-size: 0.78rem; color: var(--text); font-family: 'JetBrains Mono', monospace; }
.sub-count {
  font-size: 0.7rem; color: var(--text3); background: var(--surface2);
  padding: 0.1rem 0.5rem; border-radius: 4px; font-family: 'JetBrains Mono', monospace;
}

/* Strongest signal */
.signal-card {
  background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(168,85,247,0.06));
  border: 1px solid rgba(99,102,241,0.15); border-radius: 10px; padding: 0.8rem;
}
.signal-title { font-size: 0.85rem; font-weight: 700; margin-bottom: 0.3rem; }
.signal-score { font-family: 'JetBrains Mono', monospace; font-size: 1.3rem; font-weight: 800; color: var(--green2); }
.signal-meta { font-size: 0.72rem; color: var(--text3); margin-top: 0.2rem; }

/* Patterns */
.pattern-tag {
  display: inline-block; font-size: 0.7rem; padding: 0.25rem 0.6rem;
  border-radius: 6px; margin: 0.15rem; background: var(--surface3);
  color: var(--text2); border: 1px solid var(--border);
  font-family: 'JetBrains Mono', monospace;
}

/* ── MODAL ── */
.modal-overlay {
  display: none; position: fixed; inset: 0; background: rgba(5,5,8,0.92);
  z-index: 1000; overflow-y: auto; padding: 2rem;
  backdrop-filter: blur(8px);
}
.modal-overlay.active { display: flex; justify-content: center; align-items: flex-start; }
.modal {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 20px; max-width: 900px; width: 100%;
  margin: 2rem auto; position: relative; overflow: hidden;
}
.modal::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--tier1);
}
.modal-inner { padding: 2rem 2.5rem 2.5rem; }
.modal-close {
  position: absolute; top: 1rem; right: 1rem; background: var(--surface2);
  border: 1px solid var(--border); color: var(--text2); width: 36px; height: 36px; border-radius: 50%;
  cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center;
  z-index: 10; transition: all 0.2s;
}
.modal-close:hover { color: var(--text); background: var(--border); }

.modal-head { display: flex; gap: 1.5rem; margin-bottom: 1.5rem; align-items: flex-start; }
.modal-head-text { flex: 1; }
.modal-head h2 { font-size: 1.3rem; font-weight: 800; margin-bottom: 0.4rem; line-height: 1.3; }
.modal-head .modal-meta { display: flex; gap: 0.5rem; flex-wrap: wrap; }

.modal-radar { width: 180px; height: 180px; flex-shrink: 0; }

.modal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; margin-bottom: 1.5rem; }
.modal-section { margin-bottom: 1rem; }
.modal-section h3 {
  font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
  text-transform: uppercase; color: var(--text3); margin-bottom: 0.5rem;
  letter-spacing: 0.08em; display: flex; align-items: center; gap: 0.4rem;
}
.modal-section h3::before { content: ''; display: inline-block; width: 3px; height: 12px; background: var(--accent); border-radius: 2px; }
.modal-section p, .modal-section li { font-size: 0.88rem; color: var(--text); line-height: 1.7; }
.modal-section ul { padding-left: 1.2rem; }
.modal-section li { margin-bottom: 0.3rem; }
.modal-section.full { grid-column: 1 / -1; }

.modal-scores {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.5rem;
  margin-bottom: 1.5rem;
}
.modal-score-item {
  text-align: center; padding: 0.8rem 0.4rem;
  background: var(--surface2); border-radius: 10px; border: 1px solid var(--border);
}
.modal-score-val {
  font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 800;
}
.modal-score-val.high { color: var(--green2); }
.modal-score-val.mid { color: var(--orange); }
.modal-score-val.low { color: var(--red); }
.modal-score-label {
  font-size: 0.6rem; color: var(--text3); text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em; margin-top: 0.2rem;
}

.modal-link {
  display: inline-flex; align-items: center; gap: 0.4rem;
  color: var(--accent2); text-decoration: none; font-family: 'JetBrains Mono', monospace;
  font-size: 0.82rem; padding: 0.5rem 1rem; border: 1px solid rgba(99,102,241,0.2);
  border-radius: 8px; transition: all 0.2s;
}
.modal-link:hover { background: var(--glow-accent); border-color: var(--accent); }

/* ── EMPTY STATE ── */
.empty-state { text-align: center; padding: 6rem 2rem; color: var(--text3); }
.empty-state h2 { font-size: 1.3rem; margin-bottom: 0.5rem; color: var(--text2); font-family: 'JetBrains Mono', monospace; }

/* ── RESPONSIVE ── */
@media (max-width: 1200px) {
  .main-layout { grid-template-columns: 1fr; }
  .sidebar { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
  .stats-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 768px) {
  .ideas-grid { grid-template-columns: 1fr; }
  .container { padding: 1rem; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .modal-grid { grid-template-columns: 1fr; }
  .modal-scores { grid-template-columns: repeat(3, 1fr); }
}

/* ── ANIMATIONS ── */
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.idea-card { animation: fadeIn 0.4s ease forwards; opacity: 0; }
.idea-card:nth-child(1) { animation-delay: 0.03s; }
.idea-card:nth-child(2) { animation-delay: 0.06s; }
.idea-card:nth-child(3) { animation-delay: 0.09s; }
.idea-card:nth-child(4) { animation-delay: 0.12s; }
.idea-card:nth-child(5) { animation-delay: 0.15s; }
.idea-card:nth-child(6) { animation-delay: 0.18s; }
.idea-card:nth-child(n+7) { animation-delay: 0.2s; }

/* Export button */
.export-btn {
  background: none; border: 1px solid var(--border); color: var(--text3);
  padding: 0.5rem 0.9rem; border-radius: 8px; cursor: pointer;
  font-size: 0.75rem; font-family: 'JetBrains Mono', monospace;
  transition: all 0.2s; letter-spacing: 0.03em;
}
.export-btn:hover { border-color: var(--accent); color: var(--text); }
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="brand">
      <div class="brand-icon">&#x26B2;</div>
      <div>
        <h1><span>IDEA RADAR</span></h1>
        <div class="sub">Reddit Signal Intelligence</div>
      </div>
    </div>
    <div class="header-controls">
      <button class="export-btn" onclick="exportCSV()" title="Export CSV">&#x2B07; CSV</button>
      <div class="file-select">
        <select id="fileSelect" onchange="loadFile(this.value)"></select>
      </div>
      <button class="run-btn" onclick="runScan()" id="runBtn">&#x25B6; Scan</button>
    </div>
  </header>

  <div class="stats-grid" id="stats"></div>

  <div class="command-bar">
    <div class="search-box">
      <input type="text" id="searchInput" placeholder="Filtrer les idees..." oninput="render()">
    </div>
    <button class="filter-btn active" data-f="all" onclick="setFilter('all')">Toutes</button>
    <button class="filter-btn" data-f="tier1" onclick="setFilter('tier1')">Tier 1</button>
    <button class="filter-btn" data-f="tier2" onclick="setFilter('tier2')">Tier 2</button>
    <select class="sort-select" id="sortSelect" onchange="render()">
      <option value="score">Score &#x2193;</option>
      <option value="upvotes">Upvotes &#x2193;</option>
      <option value="comments">Comments &#x2193;</option>
      <option value="pain">Pain &#x2193;</option>
      <option value="timing">Timing &#x2193;</option>
    </select>
  </div>

  <div class="main-layout">
    <div>
      <div class="ideas-grid" id="grid"></div>
      <div class="empty-state" id="empty" style="display:none">
        <h2>// NO SIGNAL</h2>
        <p>Lance un scan pour capter des opportunites.</p>
      </div>
    </div>
    <div class="sidebar" id="sidebar"></div>
  </div>
</div>

<div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal"><div class="modal-inner" id="modalContent"></div></div>
</div>

<script>
let allIdeas = [];
let currentFilter = 'all';

async function init() {
  const res = await fetch('/api/files');
  const files = await res.json();
  const sel = document.getElementById('fileSelect');
  sel.innerHTML = files.map(f => '<option value="'+f+'">'+f+'</option>').join('');
  if (files.length) loadFile(files[0]);
  else document.getElementById('empty').style.display = 'block';
}

async function loadFile(name) {
  const res = await fetch('/api/ideas?file=' + encodeURIComponent(name));
  allIdeas = await res.json();
  currentFilter = 'all';
  document.getElementById('searchInput').value = '';
  render();
}

function getTier(idea) {
  let t = idea.tier || (idea.scoring || {}).tier;
  if (typeof t === 'string') t = parseInt(t);
  return t || 2;
}

function getComposite(idea) {
  return idea.composite_score || (idea.scoring || {}).composite || (idea.scoring || {}).composite_score || 0;
}

function getScoring(idea) {
  const s = idea.scoring || {};
  return {
    pain: s.pain_clarity || s.market_signal || 0,
    market: s.market_size || s.differentiation || 0,
    wtp: s.willingness_to_pay || s.solo_executability || 0,
    timing: s.timing || 0,
    gap: s.competition_gap || 0
  };
}

function getThread(idea) {
  return idea.source_thread || idea.market || {};
}

function getFiltered() {
  const search = (document.getElementById('searchInput').value || '').toLowerCase();
  let list = allIdeas;
  if (currentFilter === 'tier1') list = list.filter(i => getTier(i) === 1);
  else if (currentFilter === 'tier2') list = list.filter(i => getTier(i) === 2);
  if (search) {
    list = list.filter(i => {
      const p = i.problem || {};
      const t = getThread(i);
      return (p.title||'').toLowerCase().includes(search)
        || (p.description||'').toLowerCase().includes(search)
        || (t.subreddit||'').toLowerCase().includes(search);
    });
  }
  const sort = document.getElementById('sortSelect').value;
  if (sort === 'score') list.sort((a,b) => getComposite(b) - getComposite(a));
  else if (sort === 'upvotes') list.sort((a,b) => (getThread(b).score||0) - (getThread(a).score||0));
  else if (sort === 'comments') list.sort((a,b) => (getThread(b).comments||0) - (getThread(a).comments||0));
  else if (sort === 'pain') list.sort((a,b) => getScoring(b).pain - getScoring(a).pain);
  else if (sort === 'timing') list.sort((a,b) => getScoring(b).timing - getScoring(a).timing);
  return list;
}

function render() {
  const filtered = getFiltered();
  renderStats();
  renderGrid(filtered);
  renderSidebar();
  document.getElementById('empty').style.display = filtered.length ? 'none' : 'block';
  document.querySelectorAll('.filter-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.f === currentFilter);
  });
}

function setFilter(f) { currentFilter = f; render(); }

function renderStats() {
  const t1 = allIdeas.filter(i => getTier(i) === 1).length;
  const t2 = allIdeas.filter(i => getTier(i) === 2).length;
  const scores = allIdeas.map(getComposite);
  const top = scores.length ? Math.max(...scores).toFixed(1) : '--';
  const avg = scores.length ? (scores.reduce((a,b) => a+b, 0) / scores.length).toFixed(1) : '--';
  const subs = new Set(allIdeas.map(i => (getThread(i).subreddit || '').toLowerCase())).size;
  const totalUpvotes = allIdeas.reduce((sum, i) => sum + (getThread(i).score || 0), 0);

  document.getElementById('stats').innerHTML = [
    {cls:'total', label:'Signals', val:allIdeas.length, c:'c-accent', detail:totalUpvotes.toLocaleString()+' upvotes'},
    {cls:'t1', label:'Tier 1', val:t1, c:'c-t1', detail:'High conviction'},
    {cls:'t2', label:'Tier 2', val:t2, c:'c-t2', detail:'Validated risk'},
    {cls:'score', label:'Top Score', val:top, c:'c-green', detail:'/10'},
    {cls:'avg', label:'Avg Score', val:avg, c:'c-orange', detail:'/10'},
    {cls:'subs', label:'Subreddits', val:subs, c:'c-pink', detail:'sources'},
  ].map(s => '<div class="stat-card '+s.cls+'">'
    +'<div class="stat-label">'+s.label+'</div>'
    +'<div class="stat-value '+s.c+'">'+s.val+'</div>'
    +'<div class="stat-detail">'+s.detail+'</div></div>').join('');
}

function drawRadar(canvas, scoring, size) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = size || canvas.width;
  const h = size || canvas.height;
  canvas.width = w * 2; canvas.height = h * 2;
  canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
  ctx.scale(2, 2);

  const cx = w/2, cy = h/2, r = Math.min(cx, cy) - 8;
  const dims = [scoring.pain, scoring.market, scoring.wtp, scoring.timing, scoring.gap];
  const labels = ['PAIN','MKT','WTP','TIME','GAP'];
  const n = dims.length;

  for (let ring = 2; ring <= 10; ring += 2) {
    ctx.beginPath();
    for (let i = 0; i <= n; i++) {
      const angle = (Math.PI * 2 * i / n) - Math.PI/2;
      const x = cx + Math.cos(angle) * r * ring/10;
      const y = cy + Math.sin(angle) * r * ring/10;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.strokeStyle = ring === 10 ? 'rgba(30,30,48,0.8)' : 'rgba(30,30,48,0.4)';
    ctx.lineWidth = 0.5;
    ctx.stroke();
  }

  for (let i = 0; i < n; i++) {
    const angle = (Math.PI * 2 * i / n) - Math.PI/2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(angle) * r, cy + Math.sin(angle) * r);
    ctx.strokeStyle = 'rgba(30,30,48,0.5)';
    ctx.lineWidth = 0.5;
    ctx.stroke();
  }

  ctx.beginPath();
  for (let i = 0; i <= n; i++) {
    const idx = i % n;
    const angle = (Math.PI * 2 * idx / n) - Math.PI/2;
    const val = dims[idx] / 10;
    const x = cx + Math.cos(angle) * r * val;
    const y = cy + Math.sin(angle) * r * val;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.fillStyle = 'rgba(99,102,241,0.15)';
  ctx.fill();
  ctx.strokeStyle = '#6366f1';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  for (let i = 0; i < n; i++) {
    const angle = (Math.PI * 2 * i / n) - Math.PI/2;
    const val = dims[i] / 10;
    const x = cx + Math.cos(angle) * r * val;
    const y = cy + Math.sin(angle) * r * val;
    ctx.beginPath();
    ctx.arc(x, y, 2.5, 0, Math.PI*2);
    ctx.fillStyle = dims[i] >= 8 ? '#34d399' : dims[i] >= 6 ? '#f59e0b' : '#ef4444';
    ctx.fill();
  }

  ctx.font = '500 7px JetBrains Mono, monospace';
  ctx.fillStyle = '#7878a0';
  ctx.textAlign = 'center';
  for (let i = 0; i < n; i++) {
    const angle = (Math.PI * 2 * i / n) - Math.PI/2;
    const lx = cx + Math.cos(angle) * (r + 10);
    const ly = cy + Math.sin(angle) * (r + 10) + 3;
    ctx.fillText(labels[i], lx, ly);
  }
}

function renderGrid(ideas) {
  const grid = document.getElementById('grid');
  grid.innerHTML = ideas.map((idea, idx) => {
    const p = idea.problem || {};
    const sc = getScoring(idea);
    const t = getThread(idea);
    const tier = getTier(idea);
    const composite = getComposite(idea);
    const scoreClass = composite >= 8 ? 'high' : 'mid';
    const sub = t.subreddit || '';
    const globalIdx = allIdeas.indexOf(idea);
    const rank = allIdeas.slice().sort((a,b) => getComposite(b)-getComposite(a)).indexOf(idea) + 1;

    return '<div class="idea-card tier-'+tier+'" onclick="showModal('+globalIdx+')">'
      +'<div class="rank-badge '+(rank<=3?'top3':'')+'">'+rank+'</div>'
      +'<div class="idea-header">'
      +'<div class="idea-title">'+esc(p.title || p.description || '?')+'</div>'
      +'<div class="idea-composite '+scoreClass+'">'+composite.toFixed(1)+'</div>'
      +'</div>'
      +'<div class="idea-meta">'
      +'<span class="tag tier-'+tier+'">Tier '+tier+'</span>'
      +(sub ? '<span class="tag sub">r/'+esc(sub)+'</span>' : '')
      +(t.score > 500 ? '<span class="tag thread-heat">'+t.score+' pts</span>' : '')
      +'</div>'
      +'<div class="idea-desc">'+esc(p.description || '')+'</div>'
      +'<canvas class="radar-mini" id="radar-'+globalIdx+'" width="200" height="90"></canvas>'
      +'<div class="idea-footer">'
      +'<div class="thread-stats">'
      +(t.score ? '<span>&#x2B06; '+t.score+'</span>' : '')
      +(t.comments ? '<span>&#x1F4AC; '+t.comments+'</span>' : '')
      +'</div>'
      +(t.url ? '<a href="'+esc(t.url)+'" target="_blank" onclick="event.stopPropagation()">thread &#x2192;</a>' : '')
      +'</div></div>';
  }).join('');

  requestAnimationFrame(() => {
    ideas.forEach((idea, idx) => {
      const globalIdx = allIdeas.indexOf(idea);
      const canvas = document.getElementById('radar-'+globalIdx);
      if (canvas) drawRadar(canvas, getScoring(idea), 200);
    });
  });
}

function renderSidebar() {
  let html = '';

  // Strongest signal
  if (allIdeas.length) {
    const best = allIdeas.slice().sort((a,b) => getComposite(b)-getComposite(a))[0];
    const bp = best.problem || {};
    const bt = getThread(best);
    html += '<div class="sidebar-panel"><div class="sidebar-title">&#x1F3AF; Strongest Signal</div>'
      +'<div class="signal-card"><div class="signal-title">'+esc(bp.title || '')+'</div>'
      +'<div class="signal-score">'+getComposite(best).toFixed(1)+'/10</div>'
      +'<div class="signal-meta">'+esc(bt.subreddit || '')+' &bull; '+(bt.score||0)+' pts</div>'
      +'</div></div>';
  }

  // Score distribution
  const buckets = [0,0,0,0,0]; // <5, 5-6, 6-7, 7-8, 8+
  allIdeas.forEach(i => {
    const s = getComposite(i);
    if (s >= 8) buckets[4]++;
    else if (s >= 7) buckets[3]++;
    else if (s >= 6) buckets[2]++;
    else if (s >= 5) buckets[1]++;
    else buckets[0]++;
  });
  const maxB = Math.max(...buckets, 1);
  const bLabels = ['<5','5-6','6-7','7-8','8+'];
  const bColors = ['#ef4444','#f59e0b','#f59e0b','#06b6d4','#10b981'];
  html += '<div class="sidebar-panel"><div class="sidebar-title">&#x1F4CA; Score Distribution</div>';
  bLabels.forEach((l,i) => {
    html += '<div class="distrib-bar">'
      +'<div class="distrib-label">'+l+'</div>'
      +'<div class="distrib-track"><div class="distrib-fill" style="width:'+(buckets[i]/maxB*100)+'%;background:'+bColors[i]+'"></div></div>'
      +'<div class="distrib-count">'+buckets[i]+'</div></div>';
  });
  html += '</div>';

  // Subreddit breakdown
  const subMap = {};
  allIdeas.forEach(i => {
    const s = (getThread(i).subreddit || 'unknown').toLowerCase();
    subMap[s] = (subMap[s] || 0) + 1;
  });
  const subs = Object.entries(subMap).sort((a,b) => b[1]-a[1]);
  html += '<div class="sidebar-panel"><div class="sidebar-title">&#x1F4E1; Sources</div>';
  subs.forEach(([name, count]) => {
    html += '<div class="sub-row"><div class="sub-name">r/'+esc(name)+'</div><div class="sub-count">'+count+'</div></div>';
  });
  html += '</div>';

  // Detected patterns
  const patterns = [];
  const t1 = allIdeas.filter(i => getTier(i)===1);
  if (t1.length >= 3) {
    const selfhost = t1.filter(i => (getThread(i).subreddit||'').toLowerCase().includes('selfhost')).length;
    if (selfhost >= 2) patterns.push('Self-hosting dominance');
  }
  const highTiming = allIdeas.filter(i => (i.scoring||{}).timing >= 9).length;
  if (highTiming >= 3) patterns.push('Time-critical signals');
  const highPain = allIdeas.filter(i => getScoring(i).pain >= 9).length;
  if (highPain >= 3) patterns.push('Acute pain clusters');
  const avgWTP = allIdeas.reduce((s,i) => s+getScoring(i).wtp, 0) / (allIdeas.length||1);
  if (avgWTP >= 7.5) patterns.push('High WTP market');
  if (allIdeas.length > 10) patterns.push('Signal-rich scan');
  if (patterns.length === 0) patterns.push('Analyzing...');

  html += '<div class="sidebar-panel"><div class="sidebar-title">&#x1F9E0; Detected Patterns</div>'
    +'<div>'+patterns.map(p => '<span class="pattern-tag">'+p+'</span>').join('')+'</div></div>';

  document.getElementById('sidebar').innerHTML = html;
}

function showModal(globalIdx) {
  const idea = allIdeas[globalIdx];
  if (!idea) return;

  const p = idea.problem || {};
  const opp = idea.opportunity || {};
  const sc = getScoring(idea);
  const t = getThread(idea);
  const actions = idea.next_actions || idea.next_steps || [];
  const composite = getComposite(idea);
  const tier = getTier(idea);
  const rank = allIdeas.slice().sort((a,b) => getComposite(b)-getComposite(a)).indexOf(idea) + 1;

  const scoreDims = [
    {label:'Pain', val:sc.pain},
    {label:'Market', val:sc.market},
    {label:'WTP', val:sc.wtp},
    {label:'Timing', val:sc.timing},
    {label:'Gap', val:sc.gap},
  ];

  let html = '<button class="modal-close" onclick="closeModal()">&times;</button>';

  html += '<div class="modal-head">'
    +'<div class="modal-head-text">'
    +'<h2>#'+rank+' &mdash; '+esc(p.title || '')+'</h2>'
    +'<div class="modal-meta">'
    +'<span class="tag tier-'+tier+'">Tier '+tier+'</span>'
    +(t.subreddit ? '<span class="tag sub">r/'+esc(t.subreddit)+'</span>' : '')
    +'<span class="tag" style="color:var(--green2)">'+composite.toFixed(1)+'/10</span>'
    +'</div></div>'
    +'<canvas class="modal-radar" id="modal-radar" width="180" height="180"></canvas>'
    +'</div>';

  html += '<div class="modal-scores">';
  scoreDims.forEach(d => {
    const cls = d.val >= 8 ? 'high' : d.val >= 6 ? 'mid' : 'low';
    html += '<div class="modal-score-item"><div class="modal-score-val '+cls+'">'+d.val+'</div>'
      +'<div class="modal-score-label">'+d.label+'</div></div>';
  });
  html += '</div>';

  html += '<div class="modal-grid">';

  html += '<div class="modal-section"><h3>Problem</h3><p>'+esc(p.description || '')+'</p>';
  if (p.pain_intensity) html += '<p style="margin-top:0.5rem;color:var(--text2);font-size:0.82rem"><em>'+esc(p.pain_intensity)+'</em></p>';
  html += '</div>';

  if (opp.market || opp.differentiation || opp.description) {
    html += '<div class="modal-section"><h3>Opportunity</h3>'
      +'<p>'+esc(opp.market || opp.description || '')+'</p>';
    if (opp.differentiation) html += '<p style="margin-top:0.4rem;color:var(--text2);font-size:0.82rem"><strong>Edge:</strong> '+esc(opp.differentiation)+'</p>';
    if (opp.model) html += '<p style="margin-top:0.3rem;color:var(--text2);font-size:0.82rem"><strong>Model:</strong> '+esc(opp.model)+'</p>';
    if (opp.timing) html += '<p style="margin-top:0.3rem;color:var(--text2);font-size:0.82rem"><strong>Timing:</strong> '+esc(opp.timing)+'</p>';
    html += '</div>';
  }

  if (actions.length) {
    html += '<div class="modal-section full"><h3>Next Actions</h3><ul>';
    actions.forEach(a => { html += '<li>'+esc(typeof a === 'string' ? a : a.description || JSON.stringify(a))+'</li>'; });
    html += '</ul></div>';
  }

  html += '</div>';

  if (t.url) {
    html += '<a class="modal-link" href="'+esc(t.url)+'" target="_blank">&#x2197; Ouvrir le thread Reddit'
      +(t.score ? ' ('+t.score+' pts, '+t.comments+' comments)' : '')+'</a>';
  }

  document.getElementById('modalContent').innerHTML = html;
  document.getElementById('modal').classList.add('active');

  requestAnimationFrame(() => {
    const canvas = document.getElementById('modal-radar');
    if (canvas) drawRadar(canvas, sc, 180);
  });
}

function closeModal() { document.getElementById('modal').classList.remove('active'); }
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

function exportCSV() {
  const rows = [['Rank','Tier','Score','Title','Subreddit','Upvotes','Comments','Pain','Market','WTP','Timing','Gap','URL']];
  const sorted = allIdeas.slice().sort((a,b) => getComposite(b)-getComposite(a));
  sorted.forEach((idea, i) => {
    const p = idea.problem || {};
    const sc = getScoring(idea);
    const t = getThread(idea);
    rows.push([i+1, getTier(idea), getComposite(idea).toFixed(1),
      '"'+(p.title||'').replace(/"/g,'""')+'"', t.subreddit||'', t.score||0, t.comments||0,
      sc.pain, sc.market, sc.wtp, sc.timing, sc.gap, t.url||'']);
  });
  const csv = rows.map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], {type:'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'idea-radar-export.csv';
  a.click();
}

async function runScan() {
  const btn = document.getElementById('runBtn');
  btn.disabled = true; btn.textContent = 'SCANNING...'; btn.classList.add('scanning');
  try {
    const res = await fetch('/api/run', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      btn.textContent = 'DONE'; btn.classList.remove('scanning');
      setTimeout(() => { btn.innerHTML = '&#x25B6; Scan'; btn.disabled = false; init(); }, 2000);
    } else {
      btn.textContent = 'ERROR'; btn.classList.remove('scanning');
      setTimeout(() => { btn.innerHTML = '&#x25B6; Scan'; btn.disabled = false; }, 3000);
    }
  } catch(e) {
    btn.textContent = 'ERROR'; btn.classList.remove('scanning');
    setTimeout(() => { btn.innerHTML = '&#x25B6; Scan'; btn.disabled = false; }, 3000);
  }
}

init();
</script>
</body>
</html>"""


class RadarHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "":
            body = HTML_TEMPLATE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/files":
            files = self._list_files()
            self._json_response(files)
            return

        if parsed.path == "/api/ideas":
            qs = parse_qs(parsed.query)
            filename = qs.get("file", [""])[0]
            ideas = self._load_ideas(filename)
            self._json_response(ideas)
            return

        self.send_error(404)

    def do_POST(self):
        if self.path == "/api/run":
            self._run_scan()
            return
        self.send_error(404)

    def _list_files(self):
        if not OUTPUT_DIR.exists():
            return []
        files = []
        for f in sorted(OUTPUT_DIR.glob("*.json"), reverse=True):
            if f.stem.startswith(("IDEAS_", "ALL_", "TIER1_", "TIER2_")):
                files.append(f.name)
        return files

    def _load_ideas(self, filename):
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            return []
        filepath = OUTPUT_DIR / filename
        if not filepath.exists() or not filepath.suffix == ".json":
            return []
        resolved = filepath.resolve()
        if not str(resolved).startswith(str(OUTPUT_DIR.resolve())):
            return []
        try:
            with open(resolved, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
        return []

    def _run_scan(self):
        import subprocess
        script = Path(__file__).parent / "reddit_idea_radar.py"
        try:
            result = subprocess.run(
                [sys.executable, str(script), "--scrape-only"],
                capture_output=True, text=True, timeout=300,
                encoding="utf-8", errors="replace",
            )
            if result.returncode != 0:
                self._json_response({"ok": False, "error": result.stderr[:500]})
                return

            threads_file = max(OUTPUT_DIR.glob("THREADS_*.json"), key=os.path.getmtime)
            result2 = subprocess.run(
                [sys.executable, str(script), "--from-file", str(threads_file), "--local"],
                capture_output=True, text=True, timeout=600,
                encoding="utf-8", errors="replace",
            )
            self._json_response({"ok": result2.returncode == 0})
        except Exception as e:
            self._json_response({"ok": False, "error": str(e)})

    def _json_response(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle each request in its own thread (the UI fires several in parallel)."""
    daemon_threads = True


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadedHTTPServer((HOST, port), RadarHandler)
    print(f"\n  IDEA RADAR — Dashboard")
    print(f"  http://localhost:{port}")
    print(f"  Data: {OUTPUT_DIR}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")


if __name__ == "__main__":
    main()
