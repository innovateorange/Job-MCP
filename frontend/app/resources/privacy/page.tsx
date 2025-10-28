export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-black">
      <div className="max-w-4xl mx-auto px-6 py-24">
        <h1 className="text-5xl font-bold text-white mb-8">Privacy Policy</h1>
        
        <div className="space-y-8 text-white/80 leading-relaxed">
          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Data Collection</h2>
            <p>
              We collect only the information necessary to provide our services, including your 
              resume, job preferences, and application history. Your data is stored securely using 
              industry-standard encryption.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Data Usage</h2>
            <p>
              Your information is used solely to match you with relevant job opportunities and 
              automate the application process. We never sell your data to third parties.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Your Rights</h2>
            <p>
              You have full control over your data. You can view, edit, or delete your information 
              at any time through your dashboard. You can also export all your data or request 
              account deletion.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Security</h2>
            <p>
              We implement robust security measures including encryption, secure authentication, 
              and regular security audits to protect your information.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

