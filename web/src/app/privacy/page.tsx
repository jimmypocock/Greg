import Link from 'next/link';

export const metadata = {
  title: 'Privacy Policy - Songwriter',
  description: 'Privacy Policy for Songwriter',
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-800">
        <div className="max-w-4xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2">
            <svg
              className="h-8 w-8 text-indigo-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
              />
            </svg>
            <span className="text-xl font-bold text-white">Songwriter</span>
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-white mb-8">Privacy Policy</h1>

        <div className="prose prose-invert prose-gray max-w-none space-y-8 text-gray-300">
          <p className="text-sm text-gray-500">Last updated: December 2024</p>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">1. Introduction</h2>
            <p>
              This Privacy Policy explains how Songwriter (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;) collects,
              uses, and protects your personal information when you use our service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">2. Information We Collect</h2>

            <h3 className="text-lg font-medium text-white mt-4 mb-2">Account Information</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Email address</li>
              <li>Password (stored securely hashed)</li>
              <li>Account preferences and settings</li>
            </ul>

            <h3 className="text-lg font-medium text-white mt-4 mb-2">Content You Create</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Songs, lyrics, and musical compositions</li>
              <li>Audio files you upload</li>
              <li>Notes and annotations</li>
            </ul>

            <h3 className="text-lg font-medium text-white mt-4 mb-2">Usage Information</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>IP address and device information</li>
              <li>Browser type and settings</li>
              <li>Features used and actions taken</li>
              <li>Session information</li>
            </ul>

            <h3 className="text-lg font-medium text-white mt-4 mb-2">Payment Information</h3>
            <p>
              Payment processing is handled by Stripe. We do not store your full credit card
              number. We receive only limited billing information necessary to manage your subscription.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">3. How We Use Your Information</h2>
            <p>We use your information to:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Provide and maintain the Service</li>
              <li>Process your transactions</li>
              <li>Send important service updates</li>
              <li>Respond to your requests and support inquiries</li>
              <li>Improve our Service and develop new features</li>
              <li>Protect against fraud and abuse</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">4. AI and Your Content</h2>
            <p>
              When you use our AI features, your content is processed to provide suggestions
              and feedback. We:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Process your content through AI systems to provide the Service</li>
              <li>Do not sell your content or use it for advertising</li>
              <li>May use anonymized, aggregated data to improve our AI models</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">5. Data Sharing</h2>
            <p>We do not sell your personal information. We may share data with:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li><strong>Service Providers:</strong> Companies that help us operate (hosting, payment processing)</li>
              <li><strong>Legal Requirements:</strong> When required by law or to protect our rights</li>
              <li><strong>With Your Consent:</strong> When you explicitly authorize sharing</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">6. Data Security</h2>
            <p>
              We implement appropriate security measures to protect your data, including:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Encryption of data in transit (HTTPS)</li>
              <li>Secure password hashing</li>
              <li>Regular security assessments</li>
              <li>Access controls and authentication</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">7. Data Retention</h2>
            <p>
              We retain your data for as long as your account is active. When you deactivate
              your account:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Your email address is anonymized</li>
              <li>Your personal identifiers are removed</li>
              <li>Content data may be retained in anonymized form for service improvement</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">8. Your Rights</h2>
            <p>You have the right to:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li><strong>Access:</strong> Request a copy of your personal data</li>
              <li><strong>Correction:</strong> Update inaccurate information</li>
              <li><strong>Deletion:</strong> Deactivate your account and anonymize your data</li>
              <li><strong>Export:</strong> Download your content</li>
            </ul>
            <p className="mt-2">
              To exercise these rights, visit your Settings page or contact support.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">9. Cookies</h2>
            <p>
              We use essential cookies to maintain your session and preferences. We do not
              use third-party tracking cookies for advertising purposes.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">10. Children&apos;s Privacy</h2>
            <p>
              The Service is not intended for children under 13. We do not knowingly collect
              personal information from children under 13.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">11. International Users</h2>
            <p>
              Your data may be processed in countries other than your own. By using the Service,
              you consent to the transfer of your data to these countries.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">12. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. We will notify you of
              significant changes via email or through the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">13. Contact Us</h2>
            <p>
              If you have questions about this Privacy Policy or our data practices, please
              contact us through the support channels available in the application.
            </p>
          </section>
        </div>

        <div className="mt-12 pt-8 border-t border-gray-800">
          <Link href="/" className="text-indigo-400 hover:text-indigo-300">
            &larr; Back to Home
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800">
        <div className="max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
          <div className="flex justify-center gap-6 text-sm text-gray-500">
            <Link href="/terms" className="hover:text-gray-400">Terms of Service</Link>
            <Link href="/privacy" className="hover:text-gray-400">Privacy Policy</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
