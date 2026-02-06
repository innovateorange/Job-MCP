export default function SupportPage() {
  return (
    <div className="min-h-screen bg-black">
      <div className="max-w-4xl mx-auto px-6 py-24">
        <h1 className="text-5xl font-bold text-white mb-8">Support</h1>
        
        <div className="space-y-8">
          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Getting Started</h2>
            <p className="text-white/80 mb-4">
              New to Job-MCP? Check out our quick start guide to set up your profile and 
              start applying to jobs in minutes.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Frequently Asked Questions</h2>
            <div className="space-y-4">
              <div className="bg-white/5 border border-white/10 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-white mb-2">
                  How does the auto-apply feature work?
                </h3>
                <p className="text-white/70">
                  Our AI-powered system analyzes your resume and preferences, matches you with 
                  relevant job postings, and automatically submits applications on your behalf.
                </p>
              </div>
              
              <div className="bg-white/5 border border-white/10 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-white mb-2">
                  Which job sites are supported?
                </h3>
                <p className="text-white/70">
                  We currently support LinkedIn, Indeed, and several other major job boards. 
                  We&apos;re constantly adding support for more platforms.
                </p>
              </div>
              
              <div className="bg-white/5 border border-white/10 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-white mb-2">
                  Is my data secure?
                </h3>
                <p className="text-white/70">
                  Yes! We use industry-standard encryption and security practices to protect 
                  your information. See our Privacy Policy for details.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Contact Support</h2>
            <p className="text-white/80 mb-4">
              Can&apos;t find what you&apos;re looking for? Reach out to our support team:
            </p>
            <div className="bg-white/5 border border-white/10 rounded-lg p-6">
              <p className="text-white/80">
                Email: <a href="mailto:support@job-mcp.com" className="text-white hover:underline">support@job-mcp.com</a>
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

