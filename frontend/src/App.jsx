import { useEffect, useMemo, useState } from 'react'
import { api, clearSession, readSession, saveSession, signIn, signInWithSocial, signOut, signUp } from './api.js'

const BOOK_SOURCE_LABELS = { google: 'Google Books', openlib: 'Open Library', archive: 'Internet Archive', Manual: 'Personal Addition' }
const normalizeBookSource = (source) => {
  const value = (source || '').toLowerCase()
  if (value.includes('open')) return 'openlib'
  if (value.includes('archive')) return 'archive'
  if (value === 'manual' || value === 'publisher') return value
  return 'google'
}

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
    profile: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h20c0-2-3-2-3-9M10 21h4"/></>,
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
  const [form, setForm] = useState({ email: '', password: '', password2: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId) return

    const renderGoogleButton = () => {
      if (!window.google?.accounts?.id) return
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async ({ credential }) => {
          setError('')
          setBusy(true)
          try {
            onAuthenticated(await signInWithSocial('google', credential))
          } catch (err) {
            setError(err.message)
          } finally {
            setBusy(false)
          }
        },
      })
      const button = document.getElementById('google-sign-in-button')
      if (button) window.google.accounts.id.renderButton(button, { theme: 'outline', size: 'large', text: 'continue_with', width: 320 })
    }

    if (window.google?.accounts?.id) {
      renderGoogleButton()
      return
    }
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = renderGoogleButton
    document.head.appendChild(script)
  }, [onAuthenticated])

  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }))
  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'register') await signUp(form)
      const session = await signIn(form.email, form.password)
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
          <label>Email address<input type="email" autoComplete="email" value={form.email} onChange={update('email')} required placeholder="you@example.com" /></label>
          <label>Password<input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={form.password} onChange={update('password')} required placeholder="••••••••••" /></label>
          {mode === 'register' && <label>Confirm password<input type="password" autoComplete="new-password" value={form.password2} onChange={update('password2')} required placeholder="Repeat your password" /></label>}
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="button button-dark auth-submit" disabled={busy}>{busy ? 'One moment…' : mode === 'login' ? 'Open my library' : 'Create account'}<Icon name="arrow" size={18}/></button>
        </form>
        {import.meta.env.VITE_GOOGLE_CLIENT_ID && <div className="social-login"><span>or continue with</span><div id="google-sign-in-button" /></div>}
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

function ReadingActivityChart({ activity = [] }) {
  const maxPages = Math.max(1, ...activity.map((day) => day.pages))
  const activeDays = activity.filter((day) => day.pages > 0).length
  const labels = new Set([0, 5, 10, 15, 20, 25, activity.length - 1])
  const dateLabel = (value, options) => new Intl.DateTimeFormat(undefined, options).format(new Date(`${value}T12:00:00`))

  return <section className="reading-activity-card" aria-labelledby="reading-activity-title">
    <div className="reading-activity-heading"><div><p className="eyebrow">One page at a time</p><h2 id="reading-activity-title">Reading activity</h2><p>Pages logged over the last 30 days</p></div><span className="activity-summary"><strong>{activeDays}</strong><small>active days</small></span></div>
    {activeDays ? <div className="activity-chart" role="img" aria-label={`Reading activity over the last 30 days, with ${activeDays} active days`}>
      {activity.map((day, index) => <div className="activity-day" key={day.date} title={`${dateLabel(day.date, { month: 'short', day: 'numeric' })}: ${day.pages} pages`}>
        <span className="activity-bar-track"><span className={day.pages ? 'activity-bar has-pages' : 'activity-bar'} style={{ height: `${day.pages ? Math.max(8, day.pages / maxPages * 100) : 0}%` }}/></span>
        <small>{labels.has(index) ? dateLabel(day.date, { month: 'short', day: 'numeric' }) : ''}</small>
      </div>)}
    </div> : <div className="activity-empty">Update your reading progress to start building your activity chart.</div>}
  </section>
}

function BookCard({ book, entry, onAdd, onFavorite, onRemove, onProgress, onOpen, searchResult = false }) {
  const data = entry?.book || book
  const author = data.author || data.authors || 'Unknown author'
  const [pages, setPages] = useState(entry?.pages_read || 0)
  const bookId = entry?.book_id || data.id
  const previewAvailable = normalizeBookSource(data.source) === 'google' && ['PARTIAL', 'ALL_PAGES', 'ALL'].includes(data.viewability)
  return <article className={`book-card ${searchResult ? 'search-result-card' : ''}`}>
    <div className="book-card-cover-wrap"><button className="book-cover-button" onClick={() => onOpen?.(data, entry)} aria-label={`Explore ${data.title}`}><Cover src={data.cover} title={data.title}/></button>
      {entry && <span className={`status-pill ${entry.status}`}>{entry.status}</span>}
    </div>
    <div className="book-card-body">
      <div className="book-result-meta"><div className="book-meta">{(data.genre_display || data.categories || data.published_year || 'In your orbit').toString().split(',')[0]}</div>{searchResult && <span className="source-tag">{BOOK_SOURCE_LABELS[normalizeBookSource(data.source)]}</span>}{searchResult && previewAvailable && <span className="preview-tag" title="Google Books reports a preview for this title">Preview available</span>}</div>
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
  const [source, setSource] = useState('google')
  const [sourceDisplay, setSourceDisplay] = useState('Google Books')
  const [results, setResults] = useState([])
  const [sortOrder, setSortOrder] = useState('preview')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [startIndex, setStartIndex] = useState(0)
  const [nextIndex, setNextIndex] = useState(40)
  const orderedResults = useMemo(() => {
    if (sortOrder !== 'preview') return results
    return results.map((book, index) => ({ book, index })).sort((a, b) => {
      const aHasPreview = ['PARTIAL', 'ALL_PAGES', 'ALL'].includes(a.book.viewability)
      const bHasPreview = ['PARTIAL', 'ALL_PAGES', 'ALL'].includes(b.book.viewability)
      return Number(bHasPreview) - Number(aHasPreview) || a.index - b.index
    }).map(({ book }) => book)
  }, [results, sortOrder])

  const search = async (event, next = 0) => {
    event?.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError('')
    setStartIndex(next)
    try {
      const data = await api(`/books/search/?q=${encodeURIComponent(query.trim())}&source=${source}&startIndex=${next}`, { auth: false })
      setResults(data.results || [])
      setNextIndex(data.next_index || next + 40)
      setSourceDisplay(data.source_display || BOOK_SOURCE_LABELS[source])
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
    <form className="search-bar" onSubmit={(event) => search(event, 0)}><label className="search-source"><span>Search in</span><select value={source} onChange={(event) => { const nextSource = event.target.value; setSource(nextSource); setSourceDisplay(BOOK_SOURCE_LABELS[nextSource]); setResults([]); setStartIndex(0) }} aria-label="Book search source"><option value="google">Google Books</option><option value="openlib">Open Library</option><option value="archive">Internet Archive</option></select></label><Icon name="search" size={20}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="A title, author, or a feeling…" aria-label="Search books"/><button className="button button-dark" disabled={loading}>{loading ? 'Looking…' : 'Search books'}</button></form>
    {error && <div className="inline-error">{error}</div>}
    {loading && <div className="loading-state"><span className="spinner"/>Turning a few pages…</div>}
    {!loading && results.length > 0 && <>
      <div className="section-heading results-heading"><div><span className="eyebrow">Your search</span><h2>{results.length} books for “{query}”</h2></div><div className="results-controls"><span className="muted-label">{sourceDisplay}</span>{source === 'google' && <label className="results-sort">Sort by<select value={sortOrder} onChange={(event) => setSortOrder(event.target.value)} aria-label="Sort search results"><option value="preview">Preview available first</option><option value="relevance">Google Books relevance</option></select></label>}</div></div>
      <div className="book-grid search-results-grid">{orderedResults.map((book) => <BookCard key={`${book.source || source}:${book.external_id || book.google_id || `${book.title}-${book.authors}`}`} book={book} onAdd={addBook} onOpen={onOpenBook} searchResult/>)}</div>
      {results.length >= 20 && <button className="button button-outline load-more" onClick={(event) => search(event, nextIndex)}>Show me more</button>}
    </>}
    {!loading && !error && results.length === 0 && query && <div className="empty-panel"><span className="empty-icon"><Icon name="books" size={28}/></span><h3>No books found this time</h3><p>Try another title or author and we’ll look again.</p></div>}
    {!query && <div className="search-prompt"><div className="prompt-mark">“</div><p>There are whole worlds in here.<br/>Start with a title, an author, or a passing thought.</p></div>}
  </section>
}

function ProviderBookLink({ provider, url }) {
  const providerName = BOOK_SOURCE_LABELS[provider] || 'the book provider'
  return <div className="reader-launch-card">
    <span className="reader-launch-icon"><Icon name="books" size={30}/></span>
    <p className="eyebrow">{providerName}</p>
    <h3>Continue at the source</h3>
    <p className="reader-launch-copy">Open this title on {providerName}. Your LibroVault library will stay open in this tab.</p>
    <a className="button button-dark" href={url} target="_blank" rel="noreferrer">Open on {providerName} <Icon name="arrow" size={16}/></a>
    <span className="reader-launch-note">Opens in a new tab · Reading and borrowing access is set by the source</span>
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
  const initialSource = normalizeBookSource(selection.book.source)
  const [activeTab, setActiveTab] = useState(
    initialSource === 'google' ? (identifier ? 'preview' : 'details') :
      ['openlib', 'archive'].includes(initialSource) && selection.book.link ? 'preview' : 'details'
  )
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

  const source = normalizeBookSource(details.source || selection.book.source)
  const sourceName = BOOK_SOURCE_LABELS[source] || 'Book source'
  const readerLink = /^https:\/\/books\.google\.[^/]+\/books\?/.test(details.link || '') && details.link.includes('printsec=') ? details.link : null
  const googleBooksUrl = readerLink || (details.google_id
    ? `https://books.google.com/books?id=${encodeURIComponent(details.google_id)}&printsec=frontcover#v=onepage&q&f=false`
    : details.link || (details.isbn ? `https://books.google.com/books?vid=ISBN${encodeURIComponent(details.isbn)}` : 'https://books.google.com/'))
  const providerLink = details.source_links?.find((item) => item.source === source)?.url || details.link
  const sourceUrl = source === 'google' ? googleBooksUrl : providerLink
  const hasSourceReader = ['google', 'openlib', 'archive'].includes(source) && Boolean(sourceUrl)
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
          {hasSourceReader && <a className="source-link" href={sourceUrl} target="_blank" rel="noreferrer">{sourceName} <Icon name="arrow" size={15}/></a>}
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
            {hasSourceReader && <button role="tab" aria-selected={activeTab === 'preview'} className={activeTab === 'preview' ? 'active' : ''} onClick={() => setActiveTab('preview')}>{source === 'google' ? 'Read preview' : 'Open at source'}</button>}
            <button role="tab" aria-selected={activeTab === 'details'} className={activeTab === 'details' ? 'active' : ''} onClick={() => setActiveTab('details')}>Details</button>
          </div>
          {activeTab === 'preview' && hasSourceReader && <ProviderBookLink provider={source} url={sourceUrl}/>}
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

function CommunityPage({ notify }) {
  const [community, setCommunity] = useState({ discover: [], followers: [], following: [], feed: [] })
  const [reader, setReader] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(null)

  const refresh = async () => {
    setLoading(true)
    try { setCommunity(await api('/auth/community/')) }
    catch (err) { notify(err.message, true) }
    finally { setLoading(false) }
  }

  useEffect(() => { refresh() }, [])

  const openReader = async (readerId) => {
    try { setReader(await api(`/auth/community/readers/${readerId}/`)) }
    catch (err) { notify(err.message, true) }
  }

  const toggleFollow = async (readerId, follow) => {
    setBusy(readerId)
    try {
      await api(`/auth/community/readers/${readerId}/`, { method: follow ? 'POST' : 'DELETE' })
      if (reader?.reader.id === readerId) setReader(await api(`/auth/community/readers/${readerId}/`))
      await refresh()
      if (follow) notify('You’re following this reader now.')
    } catch (err) { notify(err.message, true) }
    finally { setBusy(null) }
  }

  const readerCard = (person, isFollowing = false, followsYou = false) => <article className="reader-card" key={person.id}>
    <button className="reader-avatar" onClick={() => openReader(person.id)} aria-label={`Open ${person.display_name}'s library`}>{person.avatar ? <img src={person.avatar} alt=""/> : person.display_name.slice(0, 1).toUpperCase()}</button>
    <button className="reader-card-copy" onClick={() => openReader(person.id)}><strong>{person.display_name}</strong><span>{person.book_count == null ? 'Library restricted' : person.book_count + (person.book_count === 1 ? ' book' : ' books')} · {person.follower_count} followers</span></button>
    <button className={`button ${isFollowing ? 'button-outline' : 'button-dark'} button-small`} disabled={busy === person.id || isFollowing} onClick={() => toggleFollow(person.id, true)}>{busy === person.id ? '…' : isFollowing ? 'Following' : followsYou ? 'Follow back' : 'Follow'}</button>
  </article>

  return <section className="page-content">
    <div className="page-heading"><div><p className="eyebrow">Readers make a library feel bigger</p><h1>Community</h1><p className="page-intro">Find fellow readers and see what’s on their shelves.</p></div><span className="heading-decoration"><Icon name="library" size={27}/></span></div>
    {reader ? <>
      <button className="text-link community-back" onClick={() => setReader(null)}>← Back to community</button>
      <article className="community-profile-card">
        <div className="community-profile-avatar">{reader.reader.avatar ? <img src={reader.reader.avatar} alt={reader.reader.display_name}/> : reader.reader.display_name.slice(0, 1).toUpperCase()}</div>
        <div className="community-profile-copy"><p className="eyebrow">About this reader</p><h2>{reader.reader.display_name}</h2><span className="community-profile-count">{reader.reader.follower_count} followers · {reader.reader.book_count == null ? 'Library protected' : reader.reader.book_count + ' books'}</span><p>{reader.reader.bio || 'This reader has not added a bio yet.'}</p><span className={'follow-status ' + reader.follow_status}>{reader.follow_status === 'mutual' ? 'You follow each other' : reader.follow_status === 'following' ? 'You follow this reader' : reader.follow_status === 'follows_you' ? 'This reader follows you' : 'Not following'}</span></div>
        <button className={'button ' + (reader.is_following ? 'button-outline' : 'button-dark')} onClick={() => toggleFollow(reader.reader.id, !reader.is_following)} disabled={busy === reader.reader.id}>{reader.is_following ? 'Following' : reader.follows_you ? 'Follow back' : 'Follow reader'}</button>
      </article>
      <section className="content-section community-reader-books"><div className="section-heading"><div><p className="eyebrow">Their shelf</p><h2>Books</h2></div></div>
        {!reader.can_view_library ? <div className="empty-panel protected-library"><span className="empty-icon"><Icon name="library" size={25}/></span><h3>This reader’s books are protected</h3><p>{reader.reader.library_visibility === 'mutuals' ? 'Only mutual follows can view this library. Follow them and they can follow you back to unlock it.' : 'This library is visible to followers. Follow this reader to see their books.'}</p></div> : reader.books.length ? <div className="book-grid community-book-grid">{reader.books.map((item) => <article className="community-book-card" key={item.id}><Cover src={item.cover} title={item.title}/><div><span className={`status-pill ${item.status}`}>{item.status}</span><h3>{item.title}</h3><p>{item.author}</p>{item.page_count > 0 && <small>{item.pages_read} of {item.page_count} pages read</small>}</div></article>)}</div> : <div className="empty-panel"><h3>This shelf is empty for now</h3><p>Check back when they add a book.</p></div>}
      </section>
    </> : <>
      {loading ? <div className="loading-state"><span className="spinner"/>Finding readers…</div> : <>
        <section className="content-section community-section"><div className="section-heading"><div><p className="eyebrow">People to follow</p><h2>Readers in LibroVault</h2></div><span className="muted-label">{community.discover.length} readers</span></div>{community.discover.length ? <div className="reader-grid">{community.discover.map((person) => readerCard(person))}</div> : <div className="empty-panel"><h3>No readers to discover yet</h3><p>When more people join and add books, they’ll appear here.</p></div>}</section>
        {community.followers.length > 0 && <section className="content-section community-section"><div className="section-heading"><div><p className="eyebrow">Your readers</p><h2>Followers</h2></div><span className="muted-label">{community.followers.length} people</span></div><div className="reader-grid">{community.followers.map((person) => {
          // The following list is the canonical relationship set. Derive this
          // locally too, so stale/missing serializer flags cannot offer a
          // duplicate "Follow back" action for an existing relationship.
          const alreadyFollowing = person.is_following || community.following.some((followed) => followed.id === person.id)
          return readerCard(person, alreadyFollowing, person.follows_you)
        })}</div></section>}
        {community.following.length > 0 && <section className="content-section community-section"><div className="section-heading"><div><p className="eyebrow">Your reading circle</p><h2>Following</h2></div></div><div className="reader-grid">{community.following.map((person) => readerCard(person, true))}</div></section>}
        <section className="content-section community-section"><div className="section-heading"><div><p className="eyebrow">Fresh from your circle</p><h2>Recent shelf additions</h2></div></div>{community.feed.length ? <div className="community-feed">{community.feed.map((item) => <button className="feed-item" key={item.id} onClick={() => openReader(item.reader_id)}><Cover src={item.cover} title={item.title}/><span><strong>{item.reader_name || 'A reader'}</strong><small>added <b>{item.title}</b> · {item.status}</small></span><Icon name="arrow" size={17}/></button>)}</div> : <div className="empty-panel"><h3>Your circle is quiet</h3><p>Follow readers to see their recent additions here.</p></div>}</section>
      </>}
    </>}
  </section>
}

function ProfilePage({ user, required = false, onSaved, notify }) {
  const [form, setForm] = useState({ username: user?.username || '', email: user?.email || '', first_name: user?.first_name || '', last_name: user?.last_name || '', bio: user?.profile?.bio || '', library_visibility: user?.profile?.library_visibility || 'everyone' })
  const [image, setImage] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/auth/me/').then((current) => setForm({ username: current.username || '', email: current.email || '', first_name: current.first_name || '', last_name: current.last_name || '', bio: current.profile?.bio || '', library_visibility: current.profile?.library_visibility || 'everyone' })).catch((err) => { if (required) setError(err.message) })
  }, [])

  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }))
  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const body = new FormData()
      Object.entries(form).forEach(([key, value]) => body.append(key, value))
      if (image) body.append('image', image)
      const response = await api('/auth/me/', { method: 'PATCH', body })
      onSaved(response.user)
      notify(required ? 'Username saved. Welcome to LibroVault!' : 'Your profile has been updated.')
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  return <section className={'page-content profile-page' + (required ? ' profile-setup-page' : '')}>
    <div className="page-heading"><div><p className="eyebrow">{required ? 'One last step' : 'Your account'}</p><h1>{required ? 'Choose your username' : 'Your profile'}</h1><p className="page-intro">{required ? 'Pick a name readers can recognize. You can update the rest of your profile anytime.' : 'Make your corner of LibroVault your own.'}</p></div><span className="heading-decoration"><Icon name="profile" size={27}/></span></div>
    <form className="profile-form" onSubmit={submit}>
      <div className="profile-avatar-preview">{user?.profile?.image ? <img src={user.profile.image} alt="Profile"/> : (form.username || form.email || 'R').slice(0, 1).toUpperCase()}</div>
      <label>Username<input value={form.username} onChange={update('username')} minLength="3" maxLength="30" pattern="[A-Za-z0-9_.@+-]+" required placeholder="Choose a username" autoFocus={required}/><small>Your username appears to other readers and must be unique.</small></label>
      {!required && <>
        <label>Email address<input type="email" value={form.email} onChange={update('email')} required/></label>
        <div className="profile-name-fields"><label>First name<input value={form.first_name} onChange={update('first_name')}/></label><label>Last name<input value={form.last_name} onChange={update('last_name')}/></label></div>
        <label>About you<textarea value={form.bio} onChange={update('bio')} maxLength="100" rows="3" placeholder="A little about your reading life"/></label>
        <label>Who can view your library?<select value={form.library_visibility} onChange={update('library_visibility')}><option value="everyone">Everyone on LibroVault</option><option value="followers">My followers</option><option value="mutuals">People I follow who follow me back</option></select><small>Your choice also controls book updates shown in community feeds and alerts.</small></label>
        <label>Profile photo<input type="file" accept="image/*" onChange={(event) => setImage(event.target.files?.[0] || null)}/></label>
      </>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button button-dark" disabled={busy}>{busy ? 'Saving…' : required ? 'Save username and continue' : 'Save profile'}</button>
    </form>
  </section>
}

function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [unread, setUnread] = useState(0)
  const refresh = async () => {
    try {
      const data = await api('/auth/notifications/')
      setNotifications(data.results || [])
      setUnread(data.unread_count || 0)
    } catch { /* Alerts should not block the library. */ }
  }

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 60000)
    const onFocus = () => refresh()
    window.addEventListener('focus', onFocus)
    return () => { window.clearInterval(timer); window.removeEventListener('focus', onFocus) }
  }, [])

  const markRead = async (item) => {
    if (!item.read_at) {
      await api('/auth/notifications/' + item.id + '/read/', { method: 'POST' })
      await refresh()
    }
  }
  const markAllRead = async () => {
    await api('/auth/notifications/read-all/', { method: 'POST' })
    await refresh()
  }
  const message = (item) => item.kind === 'new_follower'
    ? '@' + (item.actor_name || 'A reader') + ' followed you'
    : '@' + (item.actor_name || 'A reader') + ' finished ' + (item.book_title || 'a book')

  return <div className="notification-wrap">
    <button className="notification-button" aria-label={'Notifications' + (unread ? ', ' + unread + ' unread' : '')} aria-expanded={open} onClick={() => { setOpen((value) => !value); if (!open) refresh() }}><Icon name="bell" size={19}/>{unread > 0 && <span className="notification-count">{unread > 9 ? '9+' : unread}</span>}</button>
    {open && <section className="notification-panel"><header><strong>Notifications</strong>{unread > 0 && <button onClick={markAllRead}>Mark all read</button>}</header>{notifications.length ? <ul>{notifications.map((item) => <li key={item.id} className={item.read_at ? '' : 'unread'}><button onClick={() => markRead(item)}><span>{message(item)}</span><small>{new Date(item.created_at).toLocaleDateString()}</small></button></li>)}</ul> : <p className="notification-empty">You’re all caught up.</p>}</section>}
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

  const handleProfileSaved = (user) => {
    setSession((current) => {
      const updated = { ...current, user }
      saveSession(updated)
      return updated
    })
    if (!user.username_setup_required) setPage('home')
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
  if (!session.user?.username || session.user.username_setup_required) return <ProfilePage user={session.user} required onSaved={handleProfileSaved} notify={notify}/>

  const nav = [
    { id: 'home', label: 'Overview', icon: 'home' },
    { id: 'search', label: 'Find a book', icon: 'search' },
    { id: 'library', label: 'My library', icon: 'library' },
    { id: 'community', label: 'Community', icon: 'chart' },
    { id: 'profile', label: 'Profile', icon: 'profile' },
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
        <div className="sidebar-profile-actions"><button className="profile-chip" onClick={() => changePage('profile')}><span className="avatar">{(session.user?.first_name || session.user?.username || 'R').slice(0, 1).toUpperCase()}</span><span className="profile-copy"><strong>{session.user?.first_name || session.user?.username || 'Reader'}</strong><small>@{session.user?.username}</small></span></button><button className="signout-icon" aria-label="Sign out" title="Sign out" onClick={handleSignOut}><Icon name="logout" size={17}/></button></div>
      </div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="breadcrumbs">Your reading life <span>/</span> <strong>{nav.find((item) => item.id === page)?.label}</strong></div><div className="topbar-actions"><span className="today-date">{new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</span><NotificationBell/><button className="button button-dark button-add" onClick={() => changePage('search')}><Icon name="plus" size={17}/> Find a book</button></div></header>
      {error && <div className="global-error" role="alert">{error}<button onClick={() => setError('')}><Icon name="close" size={16}/></button></div>}
      {page === 'home' && <section className="page-content">
        <div className="welcome-panel"><div className="welcome-copy"><p className="eyebrow">Your reading room</p><h1>{greeting}, {session.user?.first_name || session.user?.email?.split('@')[0] || 'reader'}.</h1><p>Every book you make time for is a small gift to yourself.</p><button className="button button-light" onClick={() => changePage('search')}>Find something to read <Icon name="arrow" size={17}/></button></div><div className="welcome-art" aria-hidden="true"><div className="sun-disc"/><div className="art-book book-one"/><div className="art-book book-two"/><div className="art-book book-three"/><span className="art-spark">✳</span></div></div>
        <div className="stats-grid"><StatCard label="Books collected" value={dashboard?.book_count ?? 0} icon="books" tone="sage"/><StatCard label="Currently reading" value={dashboard?.reading_count ?? 0} icon="clock" tone="sand"/><StatCard label="Pages read" value={dashboard?.reading_stats?.pages_read ?? 0} icon="books" tone="rose"/><StatCard label="Books finished" value={dashboard?.reading_stats?.books_completed ?? 0} icon="check" tone="sage"/></div>
        <ReadingActivityChart activity={dashboard?.reading_stats?.activity}/>
        <section className="content-section"><div className="section-heading"><div><p className="eyebrow">A little progress adds up</p><h2>Your recent reads</h2></div><button className="text-link" onClick={() => changePage('library')}>See your library <Icon name="arrow" size={16}/></button></div>
          {loading && !dashboard ? <div className="loading-state"><span className="spinner"/>Opening your shelves…</div> : dashboard?.books?.length ? <div className="book-grid">{dashboard.books.slice(0, 3).map((entry) => <BookCard key={entry.id} entry={entry} onOpen={openBook}/>)}</div> : <div className="empty-panel"><span className="empty-icon"><Icon name="library" size={28}/></span><h3>Your shelves are waiting</h3><p>Search for a book you love and add it to your library.</p><button className="button button-outline" onClick={() => changePage('search')}><Icon name="plus" size={16}/> Find your first book</button></div>}
        </section>
        {dashboard?.popular_books?.length > 0 && <section className="content-section popular-section"><div className="section-heading"><div><p className="eyebrow">From the community</p><h2>Readers are picking up</h2></div><span className="muted-label">Popular this week</span></div><div className="book-grid">{dashboard.popular_books.slice(0, 3).map((book) => <BookCard key={book.id} book={book} onOpen={openBook}/>)}</div></section>}
      </section>}
      {page === 'search' && <SearchPage onAdded={handleBookAdded} onAddBook={addBookToLibrary} onOpenBook={openBook} notify={notify}/>}
      {page === 'community' && <CommunityPage notify={notify}/>}
      {page === 'profile' && <ProfilePage user={session.user} onSaved={handleProfileSaved} notify={notify}/>}
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
