export default function ArtBackground() {
  return (
    <div className="art-bg" aria-hidden="true">
      <div className="art-bg__blob art-bg__blob--a" />
      <div className="art-bg__blob art-bg__blob--b" />
      <div className="art-bg__blob art-bg__blob--c" />
      <div className="art-bg__grid" />
      <div className="art-bg__dots" />
      <div className="art-bg__grain" />
      <svg
        className="art-bg__contours"
        viewBox="0 0 1200 900"
        preserveAspectRatio="xMidYMid slice"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Nested contours — mark uncertainty / liquidity map */}
        <ellipse
          className="art-bg__contour art-bg__contour--d"
          cx="780"
          cy="240"
          rx="210"
          ry="92"
        />
        <ellipse
          className="art-bg__contour art-bg__contour--c"
          cx="780"
          cy="240"
          rx="150"
          ry="62"
        />
        <ellipse
          className="art-bg__contour art-bg__contour--b"
          cx="780"
          cy="240"
          rx="88"
          ry="34"
        />

        {/* Flowing strokes — mechanism boundaries */}
        <path
          className="art-bg__contour art-bg__contour--a"
          d="M-40 620 C 160 590, 260 410, 470 430 S 780 640, 1240 500"
        />
        <path
          className="art-bg__contour art-bg__contour--b"
          d="M-20 380 C 220 360, 340 220, 560 250 S 880 430, 1220 280"
        />
        <path
          className="art-bg__contour art-bg__contour--c"
          d="M 80 820 C 280 740, 420 680, 620 700 S 940 820, 1180 740"
        />
        <path
          className="art-bg__contour art-bg__contour--d"
          d="M-30 210 C 180 190, 310 80, 520 110 S 820 240, 1250 140"
        />
        <path
          className="art-bg__contour art-bg__contour--b"
          d="M-80 540 C 140 510, 300 560, 480 520 S 860 470, 1280 560"
        />

        {/* Stepped polyline — viability frontier motif */}
        <polyline
          className="art-bg__contour art-bg__contour--frontier"
          points="90,720 210,720 210,640 340,640 340,520 490,520 490,430 640,430 640,340 820,340 820,250 1040,250"
        />
      </svg>
    </div>
  );
}
