import Link from 'next/link';

export const metadata = {
  title: 'Terms of Service - Songwriter',
  description: 'Terms of Service for Songwriter',
};

export default function TermsOfServicePage() {
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
        <h1 className="text-3xl font-bold text-white mb-8">Terms of Service</h1>

        <div className="prose prose-invert prose-gray max-w-none space-y-8 text-gray-300">
          <p className="text-sm text-gray-500">Last updated: December 2024</p>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">1. Acceptance of Terms</h2>
            <p>
              By accessing or using Songwriter (&quot;the Service&quot;), you agree to be bound by these
              Terms of Service. If you do not agree to these terms, please do not use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">2. Description of Service</h2>
            <p>
              Songwriter is an AI-powered songwriting assistant that helps users write, organize,
              and improve their songs. The Service includes features such as:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Song creation and organization tools</li>
              <li>AI-powered feedback and suggestions</li>
              <li>Chord chart generation</li>
              <li>Audio analysis features</li>
              <li>Collaboration tools</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">3. User Accounts</h2>
            <p>
              To use certain features of the Service, you must create an account. You are responsible for:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Maintaining the confidentiality of your account credentials</li>
              <li>All activities that occur under your account</li>
              <li>Notifying us immediately of any unauthorized use</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">4. User Content</h2>
            <p>
              You retain ownership of all content you create using the Service, including lyrics,
              songs, and other creative works. By using the Service, you grant us a limited license
              to store and process your content solely for the purpose of providing the Service.
            </p>
            <p className="mt-2">
              You are solely responsible for your content and must ensure it does not violate any
              laws or infringe on the rights of others.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">5. AI-Generated Content</h2>
            <p>
              The Service uses artificial intelligence to provide suggestions and feedback.
              AI-generated suggestions are provided as creative assistance only. You are
              responsible for reviewing and deciding whether to use any AI-generated content.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">6. Subscription and Billing</h2>
            <p>
              Some features of the Service require a paid subscription. By subscribing, you agree to:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Pay the applicable fees for your chosen plan</li>
              <li>Automatic renewal unless you cancel before the renewal date</li>
              <li>Provide accurate billing information</li>
            </ul>
            <p className="mt-2">
              Refunds are handled on a case-by-case basis. Contact support for refund requests.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">7. Account Deactivation</h2>
            <p>
              You may deactivate your account at any time through the Settings page. Upon deactivation:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Your account will be immediately disabled</li>
              <li>Your personal information (email) will be anonymized</li>
              <li>Any active subscriptions will be cancelled</li>
              <li>Your content data will be retained in anonymized form</li>
            </ul>
            <p className="mt-2">
              Account deactivation is permanent and cannot be reversed.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">8. Prohibited Uses</h2>
            <p>You agree not to:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Use the Service for any illegal purpose</li>
              <li>Attempt to gain unauthorized access to the Service</li>
              <li>Interfere with or disrupt the Service</li>
              <li>Use automated means to access the Service without permission</li>
              <li>Upload malicious code or content</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">9. Limitation of Liability</h2>
            <p>
              The Service is provided &quot;as is&quot; without warranties of any kind. We are not liable
              for any indirect, incidental, or consequential damages arising from your use of
              the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">10. Changes to Terms</h2>
            <p>
              We may update these Terms of Service from time to time. We will notify users of
              significant changes via email or through the Service. Continued use of the Service
              after changes constitutes acceptance of the new terms.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-4">11. Contact</h2>
            <p>
              If you have questions about these Terms of Service, please contact us through
              the support channels available in the application.
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
