import React from 'react';
import ReactDOM from 'react-dom/client';
// Self-hosted (bundled by webpack, no runtime fetch to fonts.googleapis.com --
// an earlier @import there caused a real ERR_CONNECTION_RESET / page-load
// hang on this network, see README's "Animated score hero" section).
import './assets/fonts/hyperlegible-sans/hyperlegible-sans.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import '@fontsource/jetbrains-mono/600.css';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
