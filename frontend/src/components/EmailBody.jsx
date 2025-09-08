import DOMPurify from "dompurify";

/**
 * Safe renderer for email bodies.
 * - If `html` exists, sanitize and render it as real HTML.
 * - Otherwise render `text` preserving line breaks.
 *
 * Props:
 *   html?: string
 *   text?: string
 */
export default function EmailBody({ html, text }) {
  if (html && html.trim()) {
    const clean = DOMPurify.sanitize(html, {
      USE_PROFILES: { html: true },
      // If you plan to remap cid/data URLs server-side, you can allow them here.
      // Remove "data" if you don't need inline images.
      ADD_ATTR: ["target", "rel"],
    });

    return (
      <div
        className="email-body prose prose-invert max-w-none"
        dangerouslySetInnerHTML={{ __html: clean }}
      />
    );
  }

  return (
    <pre className="email-body whitespace-pre-wrap">
      {text && text.trim() ? text : "(no content)"}
    </pre>
  );
}
