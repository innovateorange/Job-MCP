export default function FeaturesPage() {
  const features = [
    {
      title: 'AI Resume Parsing',
      description: 'Upload your resume and let our AI extract and structure your experience, skills, and qualifications automatically.',
      icon: '🤖',
    },
    {
      title: 'Smart Job Matching',
      description: 'Our algorithm analyzes your profile and preferences to find the most relevant job opportunities for you.',
      icon: '🎯',
    },
    {
      title: 'Automated Applications',
      description: 'Apply to multiple jobs with a single click. Our system fills out applications using your profile data.',
      icon: '⚡',
    },
    {
      title: 'Application Tracking',
      description: 'Keep track of all your applications in one place. Monitor status, responses, and follow-ups.',
      icon: '📊',
    },
    {
      title: 'Real-time Analytics',
      description: 'Gain insights into your job search with detailed statistics and performance metrics.',
      icon: '📈',
    },
    {
      title: 'Browser Automation',
      description: 'Powered by Playwright for reliable, ethical automation across major job platforms.',
      icon: '🌐',
    },
  ];

  return (
    <div className="min-h-screen bg-black">
      <div className="max-w-6xl mx-auto px-6 py-24">
        {/* Header */}
        <div className="text-center mb-20">
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
            Powerful Features
          </h1>
          <p className="text-xl text-white/60 max-w-2xl mx-auto">
            Everything you need to streamline your job search and land your dream role
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <div
              key={index}
              className="relative group backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-8 hover:bg-white/10 hover:border-white/20 transition-all duration-300"
            >
              <div className="text-5xl mb-4">{feature.icon}</div>
              <h3 className="text-2xl font-semibold text-white mb-3">
                {feature.title}
              </h3>
              <p className="text-white/60 leading-relaxed">
                {feature.description}
              </p>
              
              {/* Hover glow effect */}
              <div className="absolute inset-0 bg-white/0 group-hover:bg-white/5 rounded-2xl blur-xl transition-all duration-500 -z-10" />
            </div>
          ))}
        </div>

        {/* CTA Section */}
        <div className="mt-20 text-center">
          <div className="relative inline-block">
            <div className="absolute inset-0 bg-white/10 blur-3xl rounded-full" />
            <a
              href="/signup"
              className="relative inline-block px-8 py-4 bg-white text-black rounded-full font-semibold hover:bg-white/90 transition-all text-lg"
            >
              Get Started Today
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

