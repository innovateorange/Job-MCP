import Link from 'next/link';

export default function ResourcesPage() {
  const resources = [
    {
      title: 'About',
      description: 'Learn more about Job-MCP and our mission to help CS students land their dream jobs with AI-powered automation.',
      href: '/resources/about',
      icon: '📖',
    },
    {
      title: 'Privacy',
      description: 'Understand how we protect your data and maintain your privacy. Read our privacy policy and data handling practices.',
      href: '/resources/privacy',
      icon: '🔒',
    },
    {
      title: 'Support',
      description: 'Get help with Job-MCP. Access documentation, FAQs, and contact our support team for assistance.',
      href: '/resources/support',
      icon: '💬',
    },
  ];

  return (
    <div className="min-h-screen bg-black">
      <div className="max-w-5xl mx-auto px-6 py-24">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-white mb-4">
            Resources
          </h1>
          <p className="text-lg text-white/60 max-w-2xl mx-auto">
            Everything you need to know about Job-MCP
          </p>
        </div>

        {/* Resource Cards */}
        <div className="grid md:grid-cols-3 gap-6">
          {resources.map((resource) => (
            <Link
              key={resource.href}
              href={resource.href}
              className="group relative bg-white/5 border border-white/10 rounded-2xl p-8 hover:bg-white/10 hover:border-white/20 transition-all duration-300"
            >
              <div className="text-4xl mb-4">{resource.icon}</div>
              <h2 className="text-2xl font-semibold text-white mb-3">
                {resource.title}
              </h2>
              <p className="text-white/60 leading-relaxed">
                {resource.description}
              </p>
              <div className="mt-6 flex items-center text-white/80 group-hover:text-white transition-colors">
                <span className="text-sm font-medium">Learn more</span>
                <svg
                  className="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

