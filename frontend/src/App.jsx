import { useEffect, useMemo, useState } from 'react'
import { api, clearSession, readSession, saveSession, signIn, signOut, signUp } from './api.js'

const Icon = ({ name, size = 20 }) => {
  const paths = {
    books: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21z"/><path d="M4 5.5v13A2.5 2.5 0 0 1 6.5 16H20M8 7h8M8 10h7"/></>,
    home: <><path d="m3 10 9-7 9 7"/><path d="M5 9v12h14V9M9 21v-7h6v7"/></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></>,
    library: <><path d="M4 4.5h3v15H4zM10.5 3.5h3v16h-3zM17 5l3 1-4 14-3-1z"/></>,
    chart: <><path d="M4 20V11M10 20V4M16 20v-7M22 20H2"/></>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
    heart: <path d="M20.8 8.7c0 5-8.8 10.3-8.8 10.3S3.2 13.7 3.2 8.7A4.7 4.7 0 0 1 12 6a4.7 4.7 0 0 1 8.8 2.7Z"/>,
    logout: <><path d="M10 17l5-5-5-5M15 12H3"/><path d="M12 3h7a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-7"/></>,
    close: <><path d="m18 6-12 12M6 6l12 12"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

function Cover({ src, title, className = '' }) {
  const [failed, setFailed] = useState(false)
  return failed || !src
    ? <div className={`cover-fallback ${className}`}><Icon name="books" size={30}/><span>{title?.slice(0, 24)}</span></div>
    : <img className={`book-cover ${className}`} src={src} alt={`Cover of ${title}`} onError={() => setFailed(true)} />
}

function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ username: '', email: '', password: '', password2: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }))
  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'register') await signUp(form)
      const session = await signIn(form.username, form.password)
      onAuthenticated(session)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return <main className="auth-page">
    <section className="auth-story">
      <div className="brand brand-light"><span className="brand-mark"><Icon name="books" size={23}/></span><span>librovault</span></div>
      <div className="story-copy">
        <p className="eyebrow">A quieter kind of reading list</p>
        <h1>Make room for<br/><em>the next chapter.</em></h1>
        <p className="story-description">Keep the books you love close. Find your next favorite. Notice how far you’ve come.</p>
      </div>
      <div className="story-note"><span className="note-line"/>A personal library for a life of reading.</div>
      <div className="story-decoration" aria-hidden="true"><span/><span/><span/></div>
    </section>
    <section className="auth-form-side">
      <div className="auth-mobile-brand brand"><span className="brand-mark"><Icon name="books" size={22}/></span><span>librovault</span></div>
      <div className="auth-card">
        <p className="eyebrow">{mode === 'login' ? 'Welcome back' : 'Your reading life starts here'}</p>
        <h2>{mode === 'login' ? 'Sign in to your library' : 'Create your account'}</h2>
        <p className="auth-subtitle">{mode === 'login' ? 'Pick up right where you left off.' : 'A little space for all the books ahead.'}</p>
        <form onSubmit={submit} className="auth-form">
          <label>Username<input autoComplete="username" value={form.username} onChange={update('username')} required placeholder="Your username" /></label>
          {mode === 'register' && <label>Email address<input type="email" autoComplete="email" value={form.email} onChange={update('email')} required placeholder="you@example.com" /></label>}
          <label>Password<input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={form.password} onChange={update('password')} required placeholder="••••••••••" /></label>
          {mode === 'register' && <label>Confirm password<input type="password" autoComplete="new-password" value={form.password2} onChange={update('password2')} required placeholder="Repeat your password" /></label>}
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="button button-dark auth-submit" disabled={busy}>{busy ? 'One moment…' : mode === 'login' ? 'Open my library' : 'Create account'}<Icon name="arrow" size={18}/></button>
        </form>
        <p className="auth-switch">{mode === 'login' ? 'New to LibroVault?' : 'Already have an account?'} <button onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>{mode === 'login' ? 'Create an account' : 'Sign in'}</button></p>
      </div>
      <p className="auth-footnote">A good book always leaves the light on.</p>
    </section>
  </main>
}

function StatCard({ label, value, icon, tone }) {
  return <article className={`stat-card ${tone}`}>
    <div className="stat-top"><span>{label}</span><span className="stat-icon"><Icon name={icon} size={19}/></span></div>
    <strong>{value ?? '—'}</strong>
  </article>
}

function BookCard({ book, entry, onAdd, onFavorite, onRemove, onProgress, onOpen, searchResult = false }) {
  const data = entry?.book || book
  const author = data.author || data.authors || 'Unknown author'
  const [pages, setPages] = useState(entry?.pages_read || 0)
  const bookId = entry?.book_id || data.id
  const previewAvailable = ['PARTIAL', 'ALL_PAGES', 'ALL'].includes(data.viewability)
  return <article className={`book-card ${searchResult ? 'search-result-card' : ''}`}>
    <div className="book-card-cover-wrap"><button className="book-cover-button" onClick={() => onOpen?.(data, entry)} aria-label={`Explore ${data.title}`}><Cover src={data.cover} title={data.title}/></button>
      {entry && <span className={`status-pill ${entry.status}`}>{entry.status}</span>}
    </div>
    <div className="book-card-body">
      <div className="book-result-meta"><div className="book-meta">{(data.genre_display || data.categories || data.published_year || 'In your orbit').toString().split(',')[0]}</div>{searchResult && previewAvailable && <span className="preview-tag" title="Google Books reports a preview for this title">Preview available</span>}</div>
      <h3><button className="book-title-button" onClick={() => onOpen?.(data, entry)}>{data.title}</button></h3>
      <p className="book-author">{author}</p>
      {entry && <div className="book-progress">
        <div className="progress-label"><span>{entry.pages_read} / {data.page_count || '—'} pages</span><span>{data.page_count ? Math.min(100, Math.round(entry.pages_read / data.page_count * 100)) : 0}%</span></div>
        <div className="progress-track"><span style={{ width: `${data.page_count ? Math.min(100, entry.pages_read / data.page_count * 100) : 0}%` }}/></div>
      </div>}
      <div className="book-card-actions">
        {onAdd && <button className="button button-small button-outline" onClick={() => onAdd(book)}><Icon name="plus" size={16}/> Add to library</button>}
        {onFavorite && <button className={`icon-button favorite-button ${entry.favourite ? 'is-favorite' : ''}`} title={entry.favourite ? 'Remove favourite' : 'Add favourite'} onClick={() => onFavorite(bookId)}><Icon name="heart" size={19}/></button>}
        {onProgress && <form className="progress-update" onSubmit={(event) => { event.preventDefault(); onProgress(bookId, Number(pages)).catch(() => {}) }}><input aria-label={`Pages read in ${data.title}`} type="number" min="0" max={data.page_count || undefined} value={pages} onChange={(event) => setPages(event.target.value)} /><button title="Save reading progress"><Icon name="check" size={16}/></button></form>}
        {onRemove && <button className="quiet-action" onClick={() => onRemove(bookId)}>Remove</button>}
      </div>
    </div>
  </article>
}

function SearchPage({ onAdded, onAddBook, onOpenBook, notify }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [startIndex, setStartIndex] = useState(0)
  const [nextIndex, setNextIndex] = useState(40)

  const search = async (event, next = 0) => {
    event?.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError('')
    setStartIndex(next)
    try {
      const data = await api(`/books/search/?q=${encodeURIComponent(query.trim())}&startIndex=${next}`, { auth: false })
      setResults(data.results || [])
      setNextIndex(data.next_index || next + 40)
    } catch (err) {
      setError(err.message)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const addBook = async (book) => {
    try {
      const entry = await onAddBook(book)
      notify(`${book.title} is in your library now.`)
      onAdded(entry)
    } catch (err) {
      notify(err.message, true)
    }
  }

  return <section className="page-content">
    <div className="page-heading"><div><p className="eyebrow">Find your next favorite</p><h1>Book search</h1><p className="page-intro">Search the shelves. When something catches your eye, make it yours.</p></div><span className="heading-decoration"><Icon name="search" size={27}/></span></div>
    <form className="search-bar" onSubmit={(event) => search(event, 0)}><Icon name="search" size={20}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="A title, author, or a feeling…" aria-label="Search books"/><button className="button button-dark" disabled={loading}>{loading ? 'Looking…' : 'Search books'}</button></form>
    {error && <div className="inline-error">{error}</div>}
    {loading && <div className="loading-state"><span className="spinner"/>Turning a few pages…</div>}
    {!loading && results.length > 0 && <>
      <div className="section-heading results-heading"><div><span className="eyebrow">Your search</span><h2>{results.length} books for “{query}”</h2></div><span className="muted-label">Google Books</span></div>
      <div className="book-grid search-results-grid">{results.map((book) => <BookCard key={book.google_id || `${book.title}-${book.authors}`} book={book} onAdd={addBook} onOpen={onOpenBook} searchResult/>)}</div>
      {results.length >= 20 && <button className="button button-outline load-more" onClick={(event) => search(event, nextIndex)}>Show me more</button>}
    </>}
    {!loading && !error && results.length === 0 && query && <div className="empty-panel"><span className="empty-icon"><Icon name="books" size={28}/></span><h3>No books found this time</h3><p>Try another title or author and we’ll look again.</p></div>}
    {!query && <div className="search-prompt"><div className="prompt-mark">“</div><p>There are whole worlds in here.<br/>Start with a title, an author, or a passing thought.</p></div>}
  </section>
}

function GoogleBookReaderLink({ googleBooksUrl }) {
  return <div className="reader-launch-card">
    <span className="reader-launch-icon"><Icon name="books" size={30}/></span>
    <p className="eyebrow">Google Books reader</p>
    <h3>Continue into the book</h3>
    <p className="reader-launch-copy">Open this title directly in Google Books. Your LibroVault library will stay open in this tab.</p>
    <a className="button button-dark" href={googleBooksUrl} target="_blank" rel="noreferrer">Open book reader <Icon name="arrow" size={16}/></a>
    <span className="reader-launch-note">Opens in a new tab · Preview access is set by Google and the publisher</span>
  </div>
}

function BookDetailsModal({ selection, onClose, onAddBook, onAdded, onProgress, notify }) {
  const [details, setDetails] = useState(selection.book)
  const [libraryEntry, setLibraryEntry] = useState(selection.entry || null)
  const [loading, setLoading] = useState(Boolean(selection.book.id))
  const [adding, setAdding] = useState(false)
  const [savingProgress, setSavingProgress] = useState(false)
  const [error, setError] = useState('')
  const identifier = details.google_id || details.isbn
  const [activeTab, setActiveTab] = useState(identifier ? 'preview' : 'details')
  const [pagesInput, setPagesInput] = useState(selection.entry?.pages_read ?? 0)

  useEffect(() => {
    const closeOnEscape = (event) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', closeOnEscape)
    document.body.classList.add('modal-open')
    return () => {
      window.removeEventListener('keydown', closeOnEscape)
      document.body.classList.remove('modal-open')
    }
  }, [onClose])

  useEffect(() => {
    let current = true
    if (!selection.book.id) return () => { current = false }
    setLoading(true)
    api(`/books/${selection.book.id}/`)
      .then((data) => {
        if (!current) return
        setDetails(data)
        if (data.library_entry) setLibraryEntry((existing) => existing || data.library_entry)
        setPagesInput(data.pages_read ?? 0)
      })
      .catch((err) => { if (current) setError(err.message) })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [selection.book.id])

  const addToLibrary = async () => {
    setAdding(true)
    setError('')
    try {
      const entry = await onAddBook(details)
      setLibraryEntry(entry)
      onAdded(entry)
      notify(`${details.title} is in your library now.`)
    } catch (err) {
      setError(err.message)
    } finally {
      setAdding(false)
    }
  }

  const updateReadingProgress = async (event) => {
    event.preventDefault()
    setSavingProgress(true)
    setError('')
    try {
      const result = await onProgress(details.id, Number(pagesInput))
      const updated = result?.library_entry
      if (updated) setLibraryEntry(updated)
      setDetails((current) => ({ ...current, pages_read: Number(pagesInput), library_entry: updated || current.library_entry }))
      notify('Reading progress saved.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingProgress(false)
    }
  }

  const readerLink = /^https:\/\/books\.google\.[^/]+\/books\?/.test(details.link || '') && details.link.includes('printsec=') ? details.link : null
  const googleBooksUrl = readerLink || (details.google_id
    ? `https://books.google.com/books?id=${encodeURIComponent(details.google_id)}&printsec=frontcover#v=onepage&q&f=false`
    : details.link || (details.isbn ? `https://books.google.com/books?vid=ISBN${encodeURIComponent(details.isbn)}` : 'https://books.google.com/'))
  const author = details.author || details.authors || 'Unknown author'
  const status = libraryEntry?.status || details.library_entry?.status
  const pagesRead = libraryEntry?.pages_read ?? details.pages_read
  const description = details.description?.trim()

  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <section className="book-dialog" role="dialog" aria-modal="true" aria-labelledby="book-dialog-title">
      <button className="dialog-close icon-button" onClick={onClose} aria-label="Close book details"><Icon name="close" size={19}/></button>
      <div className="dialog-layout">
        <div className="dialog-cover-column"><Cover src={details.cover} title={details.title} className="dialog-cover"/>
          {status && <span className={`status-pill dialog-status ${status}`}>{status}</span>}
          <a className="source-link" href={googleBooksUrl} target="_blank" rel="noreferrer">Google Books <Icon name="arrow" size={15}/></a>
        </div>
        <div className="dialog-copy">
          <p className="eyebrow">{details.genre_display || details.categories || 'A book worth discovering'}</p>
          <h2 id="book-dialog-title">{details.title}</h2>
          <p className="dialog-author">by {author}</p>
          <div className="dialog-facts">
            {details.published_year > 0 && <span>{details.published_year}</span>}
            {details.page_count > 0 && <span>{details.page_count} pages</span>}
            {details.isbn && <span>ISBN {details.isbn}</span>}
          </div>
          {loading && <div className="dialog-loading"><span className="spinner"/>Loading book details…</div>}
          {error && <p className="inline-error dialog-error">{error}</p>}
          <div className="dialog-tabs" role="tablist" aria-label="Book information">
            {identifier && <button role="tab" aria-selected={activeTab === 'preview'} className={activeTab === 'preview' ? 'active' : ''} onClick={() => setActiveTab('preview')}>Read preview</button>}
            <button role="tab" aria-selected={activeTab === 'details'} className={activeTab === 'details' ? 'active' : ''} onClick={() => setActiveTab('details')}>Details</button>
          </div>
          {activeTab === 'preview' && identifier && <GoogleBookReaderLink googleBooksUrl={googleBooksUrl}/>}
          {activeTab === 'details' && <div className="dialog-description"><h3>About this book</h3><p>{description || 'There isn’t a description for this title yet. Open Google Books for more information.'}</p></div>}
          {status && <div className="dialog-reading-state"><span className="state-icon"><Icon name={status === 'completed' ? 'check' : 'clock'} size={17}/></span><span><strong>{status === 'completed' ? 'Finished' : status === 'wishlist' ? 'On your want-to-read shelf' : 'Currently reading'}</strong>{pagesRead != null && details.page_count > 0 && <small>{pagesRead} of {details.page_count} pages read</small>}</span></div>}
          {libraryEntry && onProgress && <form className="dialog-progress-update" onSubmit={updateReadingProgress}><label htmlFor="dialog-pages-read">Update pages read</label><div><input id="dialog-pages-read" type="number" min="0" max={details.page_count || undefined} value={pagesInput} onChange={(event) => setPagesInput(event.target.value)} /><button className="button button-outline" disabled={savingProgress}>{savingProgress ? 'Saving…' : 'Save progress'}</button></div></form>}
          <div className="dialog-actions">
            {!libraryEntry && !details.library_entry && <button className="button button-dark" onClick={addToLibrary} disabled={adding}><Icon name="plus" size={17}/>{adding ? 'Adding…' : 'Add to my library'}</button>}
            {(libraryEntry || details.library_entry) && <span className="in-library-label"><Icon name="check" size={17}/> In your library</span>}
            <button className="button button-outline" onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    </section>
  </div>
}

function App() {
  const [session, setSession] = useState(() => readSession())
  const [page, setPage] = useState('home')
  const [dashboard, setDashboard] = useState(null)
  const [library, setLibrary] = useState([])
  const [libraryStatus, setLibraryStatus] = useState('')
  const [selectedBook, setSelectedBook] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState(null)

  const greeting = useMemo(() => {
    const hour = new Date().getHours()
    return hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
  }, [])

  const notify = (message, isError = false) => {
    setToast({ message, isError })
    window.setTimeout(() => setToast(null), 3600)
  }

  const loadDashboard = async () => {
    if (!readSession()) return
    setLoading(true)
    setError('')
    try {
      const data = await api('/dashboard/')
      setDashboard(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const loadLibrary = async (status = libraryStatus) => {
    if (!readSession()) return
    setLoading(true)
    setError('')
    try {
      const query = new URLSearchParams({ sort: 'date_new' })
      if (status) query.set('status', status)
      const data = await api(`/library/?${query}`)
      setLibrary(data.results || data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (session?.access) loadDashboard()
  }, [session?.access])

  useEffect(() => {
    const expired = () => {
      setSession(null)
      setDashboard(null)
      setLibrary([])
      notify('Your session expired. Please sign in again.', true)
    }
    window.addEventListener('librovault:session-expired', expired)
    return () => window.removeEventListener('librovault:session-expired', expired)
  }, [])

  const changePage = (nextPage) => {
    setPage(nextPage)
    setError('')
    if (nextPage === 'library') loadLibrary()
    if (nextPage === 'home') loadDashboard()
  }

  const handleAuth = (nextSession) => {
    saveSession(nextSession)
    setSession(nextSession)
    setPage('home')
  }

  const handleSignOut = async () => {
    await signOut()
    clearSession()
    setSession(null)
    setDashboard(null)
    setLibrary([])
    setPage('home')
  }

  const toggleFavorite = async (bookId) => {
    try {
      await api(`/library/${bookId}/favourite/`, { method: 'POST' })
      await loadLibrary()
      await loadDashboard()
      notify('Your favorites are up to date.')
    } catch (err) { notify(err.message, true) }
  }

  const saveProgress = async (bookId, pagesRead) => {
    try {
      const result = await api(`/library/${bookId}/progress/`, { method: 'POST', body: JSON.stringify({ pages_read: pagesRead }) })
      await loadLibrary()
      await loadDashboard()
      return result
    } catch (err) { notify(err.message, true); throw err }
  }

  const removeBook = async (bookId) => {
    try {
      await api(`/library/${bookId}/`, { method: 'DELETE' })
      await loadLibrary()
      await loadDashboard()
      notify('Book removed from your library.')
    } catch (err) { notify(err.message, true) }
  }

  const addBookToLibrary = async (book) => {
    const result = await api('/books/add/', { method: 'POST', body: JSON.stringify(book) })
    return result.library_entry
  }

  const handleBookAdded = (entry) => {
    setSelectedBook((current) => current ? { book: entry.book, entry } : current)
    loadDashboard()
  }

  const openBook = (book, entry = null) => setSelectedBook({ book, entry })
  const closeBook = () => setSelectedBook(null)

  if (!session?.access) return <AuthScreen onAuthenticated={handleAuth}/>

  const nav = [
    { id: 'home', label: 'Overview', icon: 'home' },
    { id: 'search', label: 'Find a book', icon: 'search' },
    { id: 'library', label: 'My library', icon: 'library' },
  ]

  return <div className="app-shell">
    <aside className="sidebar">
      <button className="brand sidebar-brand" onClick={() => changePage('home')}><span className="brand-mark"><Icon name="books" size={23}/></span><span>librovault</span></button>
      <div className="side-label">YOUR SPACE</div>
      <nav className="side-nav" aria-label="Main navigation">
        {nav.map((item) => <button key={item.id} className={`nav-item ${page === item.id ? 'active' : ''}`} onClick={() => changePage(item.id)}><Icon name={item.icon} size={19}/><span>{item.label}</span>{item.id === 'library' && dashboard?.book_count > 0 && <span className="nav-count">{dashboard.book_count}</span>}</button>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-quote"><span>“</span><p>Books are a uniquely portable magic.</p><small>— Stephen King</small></div>
        <button className="profile-chip" onClick={handleSignOut}><span className="avatar">{session.user?.username?.slice(0, 1)?.toUpperCase() || 'R'}</span><span className="profile-copy"><strong>{session.user?.username || 'Reader'}</strong><small>Personal library</small></span><span className="signout-icon"><Icon name="logout" size={17}/></span></button>
      </div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="breadcrumbs">Your reading life <span>/</span> <strong>{nav.find((item) => item.id === page)?.label}</strong></div><div className="topbar-actions"><span className="today-date">{new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</span><button className="button button-dark button-add" onClick={() => changePage('search')}><Icon name="plus" size={17}/> Find a book</button></div></header>
      {error && <div className="global-error" role="alert">{error}<button onClick={() => setError('')}><Icon name="close" size={16}/></button></div>}
      {page === 'home' && <section className="page-content">
        <div className="welcome-panel"><div className="welcome-copy"><p className="eyebrow">Your reading room</p><h1>{greeting}, {session.user?.username || 'reader'}.</h1><p>Every book you make time for is a small gift to yourself.</p><button className="button button-light" onClick={() => changePage('search')}>Find something to read <Icon name="arrow" size={17}/></button></div><div className="welcome-art" aria-hidden="true"><div className="sun-disc"/><div className="art-book book-one"/><div className="art-book book-two"/><div className="art-book book-three"/><span className="art-spark">✳</span></div></div>
        <div className="stats-grid"><StatCard label="Books collected" value={dashboard?.book_count ?? 0} icon="books" tone="sage"/><StatCard label="Currently reading" value={dashboard?.reading_count ?? 0} icon="clock" tone="sand"/><StatCard label="Favorites" value={dashboard?.favourites_count ?? 0} icon="heart" tone="rose"/></div>
        <section className="content-section"><div className="section-heading"><div><p className="eyebrow">A little progress adds up</p><h2>Your recent reads</h2></div><button className="text-link" onClick={() => changePage('library')}>See your library <Icon name="arrow" size={16}/></button></div>
          {loading && !dashboard ? <div className="loading-state"><span className="spinner"/>Opening your shelves…</div> : dashboard?.books?.length ? <div className="book-grid">{dashboard.books.slice(0, 3).map((entry) => <BookCard key={entry.id} entry={entry} onOpen={openBook}/>)}</div> : <div className="empty-panel"><span className="empty-icon"><Icon name="library" size={28}/></span><h3>Your shelves are waiting</h3><p>Search for a book you love and add it to your library.</p><button className="button button-outline" onClick={() => changePage('search')}><Icon name="plus" size={16}/> Find your first book</button></div>}
        </section>
        {dashboard?.popular_books?.length > 0 && <section className="content-section popular-section"><div className="section-heading"><div><p className="eyebrow">From the community</p><h2>Readers are picking up</h2></div><span className="muted-label">Popular this week</span></div><div className="book-grid">{dashboard.popular_books.slice(0, 3).map((book) => <BookCard key={book.id} book={book} onOpen={openBook}/>)}</div></section>}
      </section>}
      {page === 'search' && <SearchPage onAdded={handleBookAdded} onAddBook={addBookToLibrary} onOpenBook={openBook} notify={notify}/>}
      {page === 'library' && <section className="page-content">
        <div className="page-heading"><div><p className="eyebrow">Everything you’re reading, and everything you’ll read</p><h1>My library</h1><p className="page-intro">{library.length ? `${library.length} books on this shelf.` : 'Your personal collection, gathered in one place.'}</p></div><button className="button button-dark" onClick={() => changePage('search')}><Icon name="plus" size={17}/> Add a book</button></div>
        <div className="library-toolbar"><div className="filter-tabs">{[['', 'All books'], ['reading', 'Reading'], ['wishlist', 'Want to read'], ['completed', 'Finished']].map(([value, label]) => <button key={value || 'all'} className={libraryStatus === value ? 'selected' : ''} onClick={() => { setLibraryStatus(value); loadLibrary(value) }}>{label}</button>)}</div></div>
        {loading && <div className="loading-state"><span className="spinner"/>Gathering your books…</div>}
        {!loading && library.length > 0 && <div className="book-grid library-grid">{library.map((entry) => <BookCard key={entry.id} entry={entry} onFavorite={toggleFavorite} onProgress={saveProgress} onRemove={removeBook} onOpen={openBook}/>)}</div>}
        {!loading && library.length === 0 && <div className="empty-panel"><span className="empty-icon"><Icon name="library" size={28}/></span><h3>This shelf is still open</h3><p>Find a book to give it a home.</p><button className="button button-outline" onClick={() => changePage('search')}><Icon name="search" size={16}/> Search books</button></div>}
      </section>}
      <footer className="app-footer"><span>Made for the love of a good story.</span><span>LibroVault <i>·</i> Your pages, your pace</span></footer>
    </main>
    {toast && <div className={`toast ${toast.isError ? 'toast-error' : ''}`} role="status">{toast.message}</div>}
    {selectedBook && <BookDetailsModal key={`${selectedBook.book.id || selectedBook.book.google_id || selectedBook.book.title}`} selection={selectedBook} onClose={closeBook} onAddBook={addBookToLibrary} onAdded={handleBookAdded} onProgress={saveProgress} notify={notify}/>}
  </div>
}

export default App
