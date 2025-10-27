'use client';

import { useEffect, useState } from 'react';

const jobTitles = [
  'Job.',
  'Role.',
  'Opportunity.',
];

export default function AnimatedJobTitle() {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % jobTitles.length);
    }, 3000); // Change every 3 seconds

    return () => clearInterval(interval);
  }, []);

  return (
    <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
      <span className="block md:inline">Land Your Dream </span>
      <span className="relative inline-block align-top overflow-hidden">
        <span
          key={currentIndex}
          className="inline-block whitespace-nowrap animate-fade-slide"
        >
          {jobTitles[currentIndex]}
        </span>
      </span>
    </h1>
  );
}

