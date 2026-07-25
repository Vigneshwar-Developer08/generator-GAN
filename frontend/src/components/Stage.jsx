import { useEffect, useRef } from "react";

const CANVAS_SIZE = 512;

/**
 * The page's signature element and its whole thesis: a canvas of raw
 * static stands in for an unsampled latent vector z. While a request
 * is in flight, it animates like live noise. The instant a real image
 * arrives, the canvas fades out and the image fades in beneath it —
 * a literal staging of "sampling z -> x" through a DCGAN generator,
 * rather than a decorative loading spinner.
 */
export function Stage({ status, result }) {
  const canvasRef = useRef(null);
  const frameRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return undefined;

    const animating = status === "loading" || status === "idle";
    // Idle: sparse, calm static. Loading: dense, busy static — a visible "sampling" tell.
    const density = status === "loading" ? 1 : 0.32;

    const paintNoise = () => {
      const frame = ctx.createImageData(CANVAS_SIZE, CANVAS_SIZE);
      const px = frame.data;
      for (let i = 0; i < px.length; i += 4) {
        const draw = Math.random() < density;
        const shade = draw ? Math.floor(Math.random() * 90) + 10 : 0;
        px[i] = shade + 20; // faint violet-leaning noise, not neutral grayscale
        px[i + 1] = shade;
        px[i + 2] = shade + 35;
        px[i + 3] = draw ? 255 : 0;
      }
      ctx.putImageData(frame, 0, 0);
      if (animating) frameRef.current = window.requestAnimationFrame(paintNoise);
    };

    paintNoise();
    return () => {
      if (frameRef.current) window.cancelAnimationFrame(frameRef.current);
    };
  }, [status]);

  const showImage = status === "success" && result !== null;

  return (
    <div className="stage">
      <div className="stage__frame">
        <canvas
          ref={canvasRef}
          width={CANVAS_SIZE}
          height={CANVAS_SIZE}
          className={`stage__noise ${showImage ? "stage__noise--hidden" : ""}`}
          aria-hidden="true"
        />
        {result && (
          <img
            src={result.imageUrl}
            alt={result.seed !== null ? `Generated face, seed ${result.seed}` : "Generated face"}
            className={`stage__image ${showImage ? "stage__image--visible" : ""}`}
            width={CANVAS_SIZE}
            height={CANVAS_SIZE}
          />
        )}
        {status === "loading" && <p className="stage__caption">sampling z ~ N(0, 1)…</p>}
      </div>
    </div>
  );
}
