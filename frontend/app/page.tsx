import AnimatedJobTitle from '@/components/AnimatedJobTitle';

export default function Home() {
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Hero Section */}
      <main className="container mx-auto px-6 md:px-12 lg:px-16 pt-32 pb-24">
        <div className="text-center mb-32 max-w-5xl mx-auto">
          <AnimatedJobTitle />
          <p className="text-xl md:text-2xl text-gray-400 mb-10 px-4">
            AI-powered applications for students.
          </p>
          <div className="flex gap-5 justify-center items-center">
            <a
              href="/profile"
              className="bg-white text-black px-8 py-3.5 rounded-full font-semibold hover:bg-gray-200 transition-all shadow-lg text-base"
            >
              Get Started
            </a>
            <a
              href="#features"
              className="bg-transparent border border-white text-white px-8 py-3.5 rounded-full font-semibold hover:bg-white hover:text-black transition-all text-base"
            >
              Learn More
            </a>
          </div>
        </div>

        {/* Features Grid */}
        <div id="features" className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-7xl mx-auto mb-32">
          {/* Profile Creation Card */}
          <div className="bg-zinc-900 rounded-3xl p-10 md:p-12 flex flex-col justify-between min-h-[350px]">
            <div>
              <h2 className="text-2xl md:text-3xl font-bold mb-3">Profile creation</h2>
              <p className="text-gray-400 text-base md:text-lg">
                Easily build your job-ready profile with resume upload and AI parsing.
              </p>
            </div>
            <div className="mt-8 bg-zinc-800 rounded-2xl h-32 flex items-center justify-center">
              <div className="w-20 h-20 bg-zinc-700 rounded-lg"></div>
            </div>
          </div>

          {/* Auto-apply Card */}
          <div className="bg-zinc-900 rounded-3xl p-10 md:p-12 flex flex-col justify-between min-h-[350px]">
            <div className="mt-auto">
              <h2 className="text-2xl md:text-3xl font-bold mb-3">Auto-apply</h2>
              <p className="text-gray-400 text-base md:text-lg">
                Let our AI-driven system automatically apply to tailored opportunities.
              </p>
            </div>
            <div className="mt-8 bg-zinc-800 rounded-2xl h-32 flex items-center justify-center">
              <div className="w-28 h-28 bg-zinc-700 rounded-full"></div>
            </div>
          </div>

          {/* Stats Tracking Card - Full Width */}
          <div className="md:col-span-2 bg-zinc-900 rounded-3xl p-10 md:p-12 flex flex-col md:flex-row justify-between items-center min-h-[280px]">
            <div className="mb-8 md:mb-0">
              <h2 className="text-2xl md:text-3xl font-bold mb-3">Stats tracking</h2>
              <p className="text-gray-400 text-base md:text-lg max-w-md">
                Monitor application progress, stats, and real-time outcomes visually.
              </p>
            </div>
            <div className="bg-zinc-800 rounded-2xl w-full md:w-80 h-40 flex items-center justify-center">
              <div className="relative">
                <div className="w-0 h-0 border-l-[35px] border-l-transparent border-r-[35px] border-r-transparent border-b-[60px] border-b-zinc-600"></div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800 py-16">
        <div className="container mx-auto px-6 md:px-12 lg:px-16">
          <div className="flex flex-col md:flex-row justify-between items-start max-w-7xl mx-auto">
            <div className="mb-8 md:mb-0">
              <h3 className="text-xl font-bold">R&A</h3>
            </div>
            <div>
              <h4 className="text-sm font-semibold mb-4 text-gray-300">Resources</h4>
              <ul className="space-y-3">
                <li>
                  <a href="/about" className="text-gray-400 hover:text-white transition text-sm">
                    About
                  </a>
                </li>
                <li>
                  <a href="/privacy" className="text-gray-400 hover:text-white transition text-sm">
                    Privacy
                  </a>
                </li>
                <li>
                  <a href="/contact" className="text-gray-400 hover:text-white transition text-sm">
                    Contact
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
