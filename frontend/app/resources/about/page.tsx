export default function AboutPage() {
  return (
    <div className="min-h-screen bg-black">
      <div className="max-w-4xl mx-auto px-6 py-24">
        <h1 className="text-5xl font-bold text-white mb-8">About Job-MCP</h1>
        
        <div className="space-y-8 text-white/80 leading-relaxed">
          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Our Mission</h2>
            <p>
              Job-MCP is designed to streamline the job application process for CS students. 
              We use AI-powered automation to help you land your dream job faster and more efficiently.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">How It Works</h2>
            <p>
              Our platform combines intelligent resume parsing, job matching, and automated application 
              submission to save you time and increase your success rate. Simply upload your resume, 
              set your preferences, and let our AI handle the rest.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Ethical Automation</h2>
            <p>
              We prioritize ethical automation practices. Job-MCP complies with site terms of service, 
              requires your explicit consent for all actions, and includes rate limits to ensure 
              responsible usage.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

