export default function Home() {
  return (
    <main className="container mx-auto p-4">
      <h1 className="text-3xl font-bold">Welcome to Job-MCP</h1>
      <p>Create a profile, upload your resume, and let our AI apply to jobs for you.</p>
      <a href="/profile" className="mt-4 inline-block bg-blue-500 text-white px-4 py-2 rounded">Get Started</a>
    </main>
  );
}
