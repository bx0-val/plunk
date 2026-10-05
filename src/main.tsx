import React from "react";
import { createRoot } from "react-dom/client";
import { PhoneApp } from "./phone";
import { Landing } from "./landing";
import "./style.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {window.location.pathname.startsWith("/app") ? <PhoneApp /> : <Landing />}
  </React.StrictMode>,
);
