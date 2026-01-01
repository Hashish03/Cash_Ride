import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

// Import all CSS files in order
import './styles/variables.css'
import './styles/main.css'
import './styles/buttons.css'
import './styles/forms.css'
import './styles/cards.css'
import './styles/badges.css'
import './styles/modal.css'
import './styles/layout.css'
import './styles/animations.css'
import './styles/utilities.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)