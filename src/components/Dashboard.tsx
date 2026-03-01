import { useEffect, useState, useCallback, useRef } from 'react'
import {
  Database, Search, FileText, TrendingUp, Terminal, Play,
  FolderOpen, Wifi, WifiOff, Film, Music, Image, Code2, Package,
  File, X, Clock, Copy, Sun, Moon
} from 'lucide-react'
import {
  apiService, Stats, SearchResult, HealthResponse, getFileCategory, FileCategory
} from '../services/apiService'

// ---------------------------------------------------------------------------
// Category config
// ---------------------------------------------------------------------------
const CAT_CONFIG: Record<FileCategory, { label: string; icon: React.ReactNode; color: string }> = {
  video: { label: 'Videos', icon: <Film className="w-4 h-4" />, color: 'text-violet-500' },
  audio: { label: 'Audio', icon: <Music className="w-4 h-4" />, color: 'text-pink-500' },
  image: { label: 'Images', icon: <Image className="w-4 h-4" />, color: 'text-sky-500' },
  document: { label: 'Documents', icon: <FileText className="w-4 h-4" />, color: 'text-amber-500' },
  app: { label: 'Apps', icon: <Package className="w-4 h-4" />, color: 'text-emerald-500' },
  code: { label: 'Code', icon: <Code2 className="w-4 h-4" />, color: 'text-blue-500' },
  other: { label: 'Other', icon: <File className="w-4 h-4" />, color: 'text-muted-foreground' },
}

const CATEGORY_ORDER: FileCategory[] = ['video', 'audio', 'image', 'document', 'app', 'code', 'other']

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function getFileName(filePath: string) {
  return filePath.replace(/\\/g, '/').split('/').pop() || filePath
}

function getExt(filePath: string) {
  const name = getFileName(filePath)
  const dot = name.lastIndexOf('.')
  return dot > -1 ? name.slice(dot).toLowerCase() : ''
}

function formatBytes(bytes: number, decimals = 1) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  const val = parseFloat((bytes / Math.pow(k, i)).toFixed(dm))
  return `${val} ${sizes[i]}`
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  const [searchQuery, setSearchQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const [activeFilter, setActiveFilter] = useState<FileCategory | 'all'>('all')

  const [indexPath, setIndexPath] = useState('')
  const [indexing, setIndexing] = useState(false)
  const [indexMsg, setIndexMsg] = useState('')

  const [history, setHistory] = useState<string[]>([])
  const [isDark, setIsDark] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [copySuccess, setCopySuccess] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopySuccess(text)
      setTimeout(() => setCopySuccess(null), 2000)
    } catch (err) {
      console.error('Failed to copy: ', err)
    }
  }

  const isWindows = typeof navigator !== 'undefined' && /Win/i.test(navigator.platform)
  const pathPlaceholder = isWindows ? 'C:\\Users\\Name\\Documents' : '/home/user/documents'

  useEffect(() => {
    async function init() {
      try {
        const [h, s] = await Promise.all([
          apiService.getHealth(),
          apiService.getStats().catch(() => null),
        ])
        setHealth(h)
        setStats(s)
      } finally {
        setLoading(false)
      }
    }
    init()
    // Load search history from localStorage
    try {
      const saved = JSON.parse(localStorage.getItem('searchHistory') || '[]')
      if (Array.isArray(saved)) setHistory(saved)
    } catch { }
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isInput = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement

      if (e.key === '/' && !isInput) {
        e.preventDefault()
        inputRef.current?.focus()
      } else if (e.key === 'Escape') {
        if (isInput) {
          (e.target as HTMLElement).blur()
        }
        setSearchQuery('')
        setShowHistory(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme')
    const darkMode = savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)
    setIsDark(darkMode)
    if (darkMode) document.documentElement.classList.add('dark')
    else document.documentElement.classList.remove('dark')
  }, [])

  const toggleTheme = () => {
    const next = !isDark
    setIsDark(next)
    if (next) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }

  const runSearch = useCallback(async (q: string) => {
    const query = q.trim()
    if (!query) return
    setSearching(true)
    setSearchError('')
    setHasSearched(true)
    setActiveFilter('all')
    try {
      const { results: r } = await apiService.search(query, 20)
      setResults(r)
      // Save to history
      setHistory(prev => {
        const next = [query, ...prev.filter(h => h !== query)].slice(0, 10)
        localStorage.setItem('searchHistory', JSON.stringify(next))
        return next
      })
    } catch (e: any) {
      setSearchError(e.message || 'Search failed')
      setResults([])
    } finally {
      setSearching(false)
    }
  }, [])

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    setShowHistory(false)
    await runSearch(searchQuery)
  }

  const handleIndex = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!indexPath.trim()) return
    setIndexing(true)
    setIndexMsg('Indexing… this may take a while for large directories.')
    try {
      const res = await apiService.indexDirectory(indexPath.trim())
      setIndexMsg(`✓ Indexed ${res.files_indexed} files (${res.total_chunks} chunks).`)
      const newStats = await apiService.getStats().catch(() => null)
      if (newStats) setStats(newStats)
    } catch (e: any) {
      setIndexMsg(`Error: ${e.message}`)
    } finally {
      setIndexing(false)
    }
  }

  const clearResults = () => {
    setResults([])
    setHasSearched(false)
    setSearchQuery('')
    setSearchError('')
    inputRef.current?.focus()
  }

  const apiConnected = health !== null

  // Group results by file category
  const grouped = results.reduce<Record<FileCategory, SearchResult[]>>((acc, r) => {
    const cat = getFileCategory(r.file_path)
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(r)
    return acc
  }, {} as Record<FileCategory, SearchResult[]>)

  // Build tab counts
  const catCounts = CATEGORY_ORDER.filter(c => grouped[c]?.length > 0)
  const filteredResults = activeFilter === 'all' ? results : (grouped[activeFilter] || [])

  return (
    <div className="min-h-screen bg-background font-sans">

      {/* ── Header ── */}
      <header className="border-b border-border bg-card/60 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'var(--gradient-primary)' }}>
            <Database className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-foreground tracking-tight">SemanticSearch</h1>
            <p className="text-xs text-muted-foreground">
              Local AI File Search — Videos, Music, Docs, Images & more
              {health ? ` · ${health.mode.toUpperCase()} mode` : ''}
            </p>
          </div>
          <div className="ml-auto flex items-center gap-4">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
              title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <div className="flex items-center gap-2">
              {apiConnected ? <Wifi className="w-3 h-3 text-emerald-500" /> : <WifiOff className="w-3 h-3 text-destructive" />}
              <span className={`text-xs px-2 py-1 rounded-full font-medium border transition-colors ${apiConnected
                ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                : 'bg-destructive/10 text-destructive border-destructive/20'
                }`}>
                {apiConnected ? 'API Connected' : 'API Offline'}
              </span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">

        {/* ── Search Bar ── */}
        <section className="relative">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
              <input
                ref={inputRef}
                id="search-input"
                type="text"
                placeholder="Search your files — try 'invoice', 'wedding photo', 'budget report'…"
                className="w-full bg-card border border-border rounded-xl py-3.5 pl-10 pr-10 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                value={searchQuery}
                onChange={e => { setSearchQuery(e.target.value); setShowHistory(true) }}
                onFocus={() => setShowHistory(true)}
                onBlur={() => setTimeout(() => setShowHistory(false), 150)}
                autoComplete="off"
              />
              {searchQuery && (
                <button type="button" onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <button
              id="search-button"
              disabled={searching || !searchQuery.trim()}
              className="bg-primary text-primary-foreground px-6 py-2 rounded-xl text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {searching ? (
                <span className="flex items-center gap-2">
                  <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Searching…
                </span>
              ) : 'Search'}
            </button>
          </form>

          {/* Search history dropdown */}
          {showHistory && history.length > 0 && !searching && (
            <div className="absolute top-full mt-1 left-0 right-12 bg-card border border-border rounded-xl shadow-xl z-20 overflow-hidden animate-in fade-in slide-in-from-top-2">
              <div className="px-3 py-1.5 border-b border-border">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Recent searches
                </span>
              </div>
              {history.slice(0, 6).map((h, i) => (
                <button key={i} onMouseDown={() => { setSearchQuery(h); setShowHistory(false); runSearch(h) }}
                  className="w-full text-left text-sm px-4 py-2 hover:bg-muted/50 transition-colors text-foreground">
                  {h}
                </button>
              ))}
            </div>
          )}

          {!apiConnected && !loading && (
            <div className="mt-2 text-xs text-destructive font-mono">
              ⚠ Backend offline — run: <code className="bg-muted px-1 rounded">python main.py serve</code>
            </div>
          )}
          {searchError && <div className="mt-2 text-xs text-destructive">⚠ {searchError}</div>}
        </section>

        {/* ── Results / Empty State ── */}
        {hasSearched ? (
          <section className="space-y-4">
            {/* Summary Line */}
            <div className="text-xs text-muted-foreground px-1 flex items-center gap-2 animate-in fade-in slide-in-from-left-2">
              <div className="w-1 h-1 rounded-full bg-primary/40" />
              <span>
                Found <span className="text-foreground font-semibold">{results.length}</span> {results.length === 1 ? 'result' : 's'}
                across <span className="text-foreground font-semibold">{catCounts.length}</span> {catCounts.length === 1 ? 'category' : 'categories'}
                for <span className="italic text-foreground font-medium">"{searchQuery}"</span>
              </span>
            </div>

            {/* Filter tabs + clear */}
            <div className="flex items-center gap-1 border-b border-border flex-wrap">
              <TabBtn active={activeFilter === 'all'} onClick={() => setActiveFilter('all')}
                icon={<Search className="w-3 h-3" />} label="All" count={results.length} />
              {catCounts.map(cat => (
                <TabBtn key={cat} active={activeFilter === cat} onClick={() => setActiveFilter(cat)}
                  icon={<span className={CAT_CONFIG[cat].color}>{CAT_CONFIG[cat].icon}</span>}
                  label={CAT_CONFIG[cat].label} count={grouped[cat]?.length ?? 0} />
              ))}
              <button onClick={clearResults}
                className="ml-auto text-muted-foreground hover:text-foreground p-1.5 rounded mb-0.5 transition-colors" title="Clear">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Result list */}
            {filteredResults.length > 0 ? (
              <div className="bg-card border border-border rounded-xl overflow-hidden shadow-sm divide-y divide-border animate-in fade-in slide-in-from-top-2">
                {filteredResults.map((res, i) => {
                  const fileName = getFileName(res.file_path)
                  const ext = getExt(res.file_path)
                  const cat = getFileCategory(res.file_path)
                  const cfg = CAT_CONFIG[cat]
                  return (
                    <div key={i} className="p-4 hover:bg-muted/30 transition-colors flex items-start gap-3 group relative">
                      {/* Icon */}
                      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 bg-muted/60 ${cfg.color}`}>
                        {cfg.icon}
                      </div>
                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-semibold text-foreground truncate">{fileName}</p>
                          <div className="flex items-center gap-2 shrink-0">
                            {/* Hover Actions */}
                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={(e) => { e.stopPropagation(); copyToClipboard(res.file_path) }}
                                className="p-1 px-1.5 rounded bg-muted hover:bg-accent hover:text-accent-foreground text-[10px] text-muted-foreground flex items-center gap-1 transition-colors"
                                title="Copy full path"
                              >
                                {copySuccess === res.file_path ? 'Copied!' : <><Copy className="w-3 h-3" /> Path</>}
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const lastSlash = res.file_path.lastIndexOf('/')
                                  const dir = lastSlash > -1 ? res.file_path.slice(0, lastSlash) : '.'
                                  apiService.openFolder(dir)
                                }}
                                className="p-1 px-1.5 rounded bg-muted hover:bg-accent hover:text-accent-foreground text-[10px] text-muted-foreground flex items-center gap-1 transition-colors"
                                title="Open containing folder"
                              >
                                <FolderOpen className="w-3 h-3" />
                                Folder
                              </button>
                            </div>
                            <span className="text-[10px] font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded shrink-0">
                              {(res.score * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                        {/* For text files show a snippet; for media files just show the path */}
                        {cat !== 'video' && cat !== 'audio' && cat !== 'image' && cat !== 'app' && res.text && (
                          <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5 italic">"{res.text}"</p>
                        )}
                        <p className="text-[10px] text-muted-foreground/60 truncate mt-1 font-mono">{res.file_path}</p>
                        <span className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded mt-1 inline-block bg-muted ${cfg.color}`}>
                          {cfg.label}{ext ? ` · ${ext}` : ''}
                          {res.file_size_bytes !== undefined && ` · ${formatBytes(res.file_size_bytes)}`}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              !searching && (
                <div className="text-center py-16 space-y-2 text-muted-foreground">
                  <Search className="w-10 h-10 mx-auto opacity-20" />
                  <p className="text-sm font-medium">No results found</p>
                  <p className="text-xs">Try a different word, or index a directory that contains your files.</p>
                </div>
              )
            )}
          </section>
        ) : (
          apiConnected && (
            <div className="bg-card border border-border rounded-2xl p-8 text-center space-y-8 shadow-sm animate-in fade-in slide-in-from-bottom-4 duration-700 fill-mode-both">
              <div className="max-w-md mx-auto space-y-2">
                <h2 className="text-xl font-bold text-foreground">Getting Started</h2>
                <p className="text-sm text-muted-foreground">Follow these 3 simple steps to start searching your local files with AI.</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
                {[
                  { step: 1, title: 'Index a directory', desc: 'Enter a folder path below and click Start to process your files.', icon: <FolderOpen className="w-5 h-5 text-amber-500" /> },
                  { step: 2, title: 'Type a query', desc: 'Use natural language like "tax documents" or "wedding photos".', icon: <Search className="w-5 h-5 text-blue-500" /> },
                  { step: 3, title: 'Browse results', desc: 'Filter by category and preview snippets instantly.', icon: <FileText className="w-5 h-5 text-emerald-500" /> },
                ].map(({ step, title, desc, icon }) => (
                  <div key={step} className="bg-muted/30 rounded-xl p-5 border border-border/50 relative overflow-hidden group hover:border-primary/30 transition-all hover:shadow-md">
                    <div className="absolute top-0 right-0 w-16 h-16 -mr-6 -mt-6 bg-primary/5 rounded-full group-hover:bg-primary/10 transition-colors" />
                    <div className="mb-4 relative">
                      <div className="w-10 h-10 rounded-lg bg-background border border-border flex items-center justify-center shadow-sm">
                        {icon}
                      </div>
                      <span className="absolute -top-2 -left-2 w-5 h-5 rounded-full bg-primary text-[10px] font-bold text-primary-foreground flex items-center justify-center">
                        {step}
                      </span>
                    </div>
                    <h3 className="text-sm font-semibold text-foreground mb-1">{title}</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
                  </div>
                ))}
              </div>
            </div>
          )
        )}

        {/* ── Stat Cards ── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard icon={<FileText className="w-4 h-4" />} label="Indexed Chunks" value={stats?.total_chunks ?? 0} />
          <StatCard icon={<TrendingUp className="w-4 h-4" />} label="Index Size (MB)" value={stats ? parseFloat(stats.index_size_mb.toFixed(2)) : 0} />
          <StatCard icon={<Film className="w-4 h-4" />} label="Results Found" value={results.length} />
        </div>

        {/* ── Two-column ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          <Section title="Index a Directory" icon={<FolderOpen className="w-4 h-4" />}>
            <div className="p-4">
              <form onSubmit={handleIndex} className="flex flex-col gap-3">
                <p className="text-xs text-muted-foreground">
                  Point to any folder — documents, movies, music, photos are all indexed automatically.
                </p>
                <div className="flex gap-2">
                  <input
                    id="index-path-input"
                    type="text"
                    placeholder={pathPlaceholder}
                    className="flex-1 bg-muted/40 border border-border rounded-lg px-3 py-2 text-xs font-mono outline-none focus:border-primary"
                    value={indexPath}
                    onChange={e => setIndexPath(e.target.value)}
                  />
                  <button
                    id="index-button"
                    disabled={indexing || !apiConnected}
                    className="bg-foreground text-background px-4 py-2 rounded-lg text-xs font-medium hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
                  >
                    {indexing
                      ? <div className="w-3 h-3 border-2 border-background/30 border-t-background rounded-full animate-spin" />
                      : <Play className="w-3 h-3" />}
                    {indexing ? 'Indexing…' : 'Start'}
                  </button>
                </div>
                <div className="flex items-center gap-2 px-1">
                  <span className="text-[10px] font-medium text-muted-foreground bg-muted px-1.5 py-0.5 rounded uppercase tracking-wider">Indexed:</span>
                  <span className="text-[10px] text-muted-foreground/70 font-mono">.txt, .md, .pdf, .docx + all media (names)</span>
                </div>
                {indexMsg && (
                  <div className={`p-2 rounded-lg border text-[10px] font-medium animate-in fade-in ${indexMsg.startsWith('Error')
                    ? 'bg-destructive/10 text-destructive border-destructive/20'
                    : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                    }`}>
                    {indexMsg}
                  </div>
                )}
              </form>
            </div>
          </Section>

          <Section title="CLI Reference" icon={<Terminal className="w-4 h-4" />}>
            <div className="p-4 space-y-3">
              {[
                { label: 'Local mode (UI + API)', cmd: 'python main.py serve' },
                { label: 'Index a directory', cmd: 'python main.py index /path/to/dir' },
                { label: 'Search from CLI', cmd: 'python main.py search "inception"' },
                { label: 'Show index stats', cmd: 'python main.py stats' },
              ].map(({ label, cmd }, i) => (
                <div key={i} className="space-y-0.5">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</p>
                  <div className="flex items-center gap-2 bg-muted/60 rounded-lg px-3 py-2 border border-border">
                    <span className="text-primary font-mono text-xs select-none">$</span>
                    <code className="text-xs font-mono text-foreground">{cmd}</code>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        </div>
      </main>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function TabBtn({
  active, onClick, icon, label, count
}: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string; count: number }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-2 rounded-t text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${active
        ? 'border-primary text-primary bg-primary/5'
        : 'border-transparent text-muted-foreground hover:text-foreground'
        }`}
    >
      {icon}
      {label}
      <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${active ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'
        }`}>{count}</span>
    </button>
  )
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-primary/10 text-primary">{icon}</div>
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-2xl font-bold text-foreground tabular-nums">{value.toLocaleString()}</p>
    </div>
  )
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-muted/20">
        <span className="text-primary">{icon}</span>
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      </div>
      {children}
    </div>
  )
}
