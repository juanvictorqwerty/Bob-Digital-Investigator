import { afterEach, expect } from "bun:test";
import { GlobalRegistrator } from "@happy-dom/global-registrator";

// Register happy-dom as the global DOM environment
GlobalRegistrator.register();

// Clean up after each test
afterEach(() => {
  document.body.innerHTML = "";
});