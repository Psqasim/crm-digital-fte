interface NexaFlowLogoProps {
  size?: "sm" | "lg";
}

export default function NexaFlowLogo({ size = "sm" }: NexaFlowLogoProps) {
  const svgSize = size === "lg" ? 40 : 24;
  const textClass = size === "lg" ? "text-2xl" : "text-xl";

  return (
    <div className="flex items-center gap-2">
      <svg
        width={svgSize}
        height={svgSize}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <path
          d="M13 2L4.5 13.5H11L10 22L19.5 10.5H13L13 2Z"
          fill="#3B82F6"
          stroke="#3B82F6"
          strokeWidth="0.5"
          strokeLinejoin="round"
        />
      </svg>
      <span className={`font-bold ${textClass} text-white hidden sm:inline`}>
        NexaFlow
      </span>
    </div>
  );
}
