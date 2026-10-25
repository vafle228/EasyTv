import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { NowPlayingProvider } from "./nowPlaying";
import { Router } from "./router";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Router>
      <NowPlayingProvider>
        {/* .et is the design system's root: container queries switch layouts to the phone version under 640px */}
        <div className="et">
          <App />
        </div>
      </NowPlayingProvider>
    </Router>
  </StrictMode>,
);
