import { useEffect, useRef } from "react";

const particles = Array.from({ length: 24 }, (_, index) => ({
  id: index,
  style: {
    "--x": `${4 + (index * 43) % 91}%`,
    "--y": `${8 + (index * 29) % 80}%`,
    "--size": `${2 + index % 3}px`,
    "--opacity": 0.22 + index % 5 * 0.09,
    "--duration": `${6 + index % 5 * 1.4}s`,
    "--delay": `${index * -0.38}s`,
    "--drift-x": `${(index % 4 - 2) * 10}px`,
    "--drift-y": `${(index % 5 - 2) * -13}px`,
  },
}));

/** Decorative-only landing artwork. It never reads or writes application data. */
export function EventOperationsVisual() {
  const sceneRef = useRef(null);
  const frameRef = useRef(null);

  useEffect(() => () => {
    if (frameRef.current) cancelAnimationFrame(frameRef.current);
  }, []);

  const handlePointerMove = (event) => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const scene = sceneRef.current;
    if (!scene) return;
    const bounds = scene.getBoundingClientRect();
    const x = ((event.clientX - bounds.left) / bounds.width - 0.5) * 2;
    const y = ((event.clientY - bounds.top) / bounds.height - 0.5) * 2;
    if (frameRef.current) cancelAnimationFrame(frameRef.current);
    frameRef.current = requestAnimationFrame(() => {
      scene.style.setProperty("--pointer-x", x.toFixed(3));
      scene.style.setProperty("--pointer-y", y.toFixed(3));
    });
  };

  const resetPointer = () => {
    const scene = sceneRef.current;
    if (!scene) return;
    scene.style.setProperty("--pointer-x", "0");
    scene.style.setProperty("--pointer-y", "0");
  };

  return <div className="hero-visual-wrap" onPointerMove={handlePointerMove} onPointerLeave={resetPointer}>
    <div className="hero-visual hero-visual--v2" ref={sceneRef} aria-hidden="true">
      <div className="visual-spotlight" />
      <div className="visual-grid" />
      <div className="visual-particles">{particles.map((particle) => <i key={particle.id} style={particle.style} />)}</div>
      <div className="orbit orbit--outer"><span className="orbit-node orbit-node--workshop">Workshop</span><span className="orbit-node orbit-node--seminar">Seminar</span></div>
      <div className="orbit orbit--inner"><span className="orbit-node orbit-node--community">Community</span><span className="orbit-node orbit-node--checkin">Check-in</span></div>
      <div className="visual-core"><span>N<span>•</span></span><small>Event operations</small><b>● Live platform</b></div>
      <div className="visual-node visual-node--one"><strong>Registration</strong>Confirmation flow</div>
      <div className="visual-node visual-node--two"><strong>Capacity</strong>Availability signal</div>
      <div className="visual-node visual-node--three"><strong>Attendees</strong>Check-in ready</div>
      <div className="visual-flow visual-flow--one" /><div className="visual-flow visual-flow--two" />
    </div>
  </div>;
}
