import "@/styles/global.css";

import { StrictMode } from "react";
import ReactDOM from "react-dom/client";

import { bootstrap } from "@/app/bootstrap";
import { Root } from "@/app/Root";

bootstrap();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
