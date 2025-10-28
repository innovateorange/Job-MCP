import AnimatedJobTitle from '@/components/AnimatedJobTitle';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Hero Section */}
      <main className="container mx-auto px-6 md:px-12 lg:px-20 pt-32 pb-24">
        <div className="text-center mb-20 max-w-5xl mx-auto">
          <AnimatedJobTitle />
          <p className="text-xl md:text-2xl text-gray-400 mb-10 px-4">
            AI-powered applications for students.
          </p>
          <div className="flex gap-5 justify-center items-center">
            <Link
              href="/dashboard"
              className="bg-white text-black px-8 py-3.5 rounded-full font-semibold hover:bg-gray-200 transition-all shadow-lg text-base"
            >
              Get Started
            </Link>
            <Link
              href="#features"
              className="bg-transparent border border-white text-white px-8 py-3.5 rounded-full font-semibold hover:bg-white hover:text-black transition-all text-base"
            >
              Learn More
            </Link>
          </div>
        </div>

        {/* Features Grid - Bento Style */}
        <div id="features" className="max-w-6xl mx-auto mb-32">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8">
            {/* Profile Creation Card - Top Left */}
            <div className="bg-zinc-900/50 backdrop-blur rounded-3xl p-8 md:p-10 flex flex-col justify-between min-h-[400px] md:min-h-[450px] border border-white/5">
              <div>
                <h2 className="text-3xl md:text-4xl font-semibold mb-4">Profile creation</h2>
                <p className="text-gray-400 text-lg leading-relaxed max-w-xs">
                  Easily build your job-ready profile with resume upload and AI parsing.
                </p>
              </div>
              <div className="mt-auto pt-12 flex justify-center">
                <div className="w-32 h-32 bg-zinc-800/80 rounded-2xl border border-white/5"></div>
              </div>
            </div>

            {/* Auto-apply Card - Top Right (Taller) */}
            <div className="bg-zinc-900/50 backdrop-blur rounded-3xl p-8 md:p-10 flex flex-col min-h-[400px] md:min-h-[500px] row-span-1 border border-white/5">
              <div className="mt-auto pt-12 flex justify-center">
                <div className="w-36 h-36 bg-zinc-800/80 rounded-full border border-white/5"></div>
              </div>
              <div className="mt-12">
                <h2 className="text-3xl md:text-4xl font-semibold mb-4">Auto-apply</h2>
                <p className="text-gray-400 text-lg leading-relaxed max-w-xs">
                  Let our AI-driven system automatically apply to tailored opportunities.
                </p>
              </div>
            </div>

            {/* Stats Tracking Card - Bottom Left (Wider) */}
            <div className="md:col-span-2 bg-zinc-900/50 backdrop-blur rounded-3xl p-8 md:p-10 flex flex-col md:flex-row justify-between items-end min-h-[350px] md:min-h-[400px] border border-white/5">
              <div className="mb-8 md:mb-0">
                <h2 className="text-3xl md:text-4xl font-semibold mb-4">Stats tracking</h2>
                <p className="text-gray-400 text-lg leading-relaxed max-w-md">
                  Monitor application progress, stats, and real-time outcomes visually.
                </p>
              </div>
              <div className="flex items-center justify-center w-full md:w-auto">
                <div className="relative">
                  <div 
                    className="w-0 h-0"
                    style={{
                      borderLeft: '50px solid transparent',
                      borderRight: '50px solid transparent',
                      borderBottom: '90px solid rgb(39 39 42 / 0.8)',
                    }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800/50 py-20">
        <div className="container mx-auto px-6 md:px-12 lg:px-20">
          <div className="flex flex-col md:flex-row justify-between items-start max-w-6xl mx-auto">
            <div className="mb-8 md:mb-0">
              <h3 className="text-2xl font-semibold">R&A</h3>
            </div>
            <div>
              <h4 className="text-sm font-medium mb-6 text-gray-400">Resources</h4>
              <ul className="space-y-3">
                <li>
                  <Link href="/resources/about" className="text-gray-500 hover:text-white transition text-sm">
                    About
                  </Link>
                </li>
                <li>
                  <Link href="/resources/privacy" className="text-gray-500 hover:text-white transition text-sm">
                    Privacy
                  </Link>
                </li>
                <li>
                  <Link href="/resources/support" className="text-gray-500 hover:text-white transition text-sm">
                    Contact
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
