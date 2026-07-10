import React, { useState } from "react";

interface SourceLogoProps {
  source: string;
  url: string;
  className?: string;
}

export const SourceLogo: React.FC<SourceLogoProps> = ({ source, url, className = "" }) => {
  const [logoFailed, setLogoFailed] = useState(false);
  const [useFavicon, setUseFavicon] = useState(false);

  let domain = "";
  try {
    if (url) {
      domain = new URL(url).hostname;
    }
  } catch (e) {
    // Catch invalid URLs gracefully
  }

  if (domain && !logoFailed) {
    const src = useFavicon 
      ? `https://www.google.com/s2/favicons?domain=${domain}&sz=64`
      : `https://logo.clearbit.com/${domain}`;
      
    return (
      <img
        src={src}
        alt={source}
        onError={() => {
          if (!useFavicon) {
            setUseFavicon(true);
          } else {
            setLogoFailed(true);
          }
        }}
        className={`h-4.5 object-contain max-w-[90px] rounded-sm ${useFavicon ? 'w-4 h-4' : ''} ${className}`}
      />
    );
  }

  return (
    <span className={`text-[10px] text-slate-500 font-bold uppercase tracking-wider ${className}`}>
      {source}
    </span>
  );
};
