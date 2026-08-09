import { useEffect, useState } from "react";

// Shared by every ambient WebGL background (Strands) on the page -- skips
// mounting the canvas entirely under the OS-level reduced-motion setting,
// not just pausing a CSS animation, so those users don't pay the GPU cost.
export default function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return reduced;
}
