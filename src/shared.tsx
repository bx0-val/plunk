import { ArrowUpRight } from "lucide-react";
export function Wordmark({ small = false }: { small?: boolean }) {
  return (
    <a
      className={`wordmark ${small ? "small" : ""}`}
      href="/"
      aria-label="Plunk home"
    >
      plunk<span>.</span>
    </a>
  );
}
export function Footer() {
  return (
    <footer>
      <Wordmark small />
      <span>A little less friction. A little more doing.</span>
      <a href="/app">
        Open Plunk <ArrowUpRight size={16} />
      </a>
    </footer>
  );
}
