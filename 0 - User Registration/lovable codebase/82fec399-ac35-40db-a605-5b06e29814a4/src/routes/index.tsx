import { createFileRoute, useRouter } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { ArrowRight, Check, LockKeyhole, Menu, Network, Sparkles, Upload, X } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createAccount } from "@/lib/signup.functions";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "The Fellowship — Meet people by what they're thinking about" },
      { name: "description", content: "A private discovery network that connects people through the ideas emerging in their AI conversations." },
      { property: "og:title", content: "The Fellowship — Ideas that connect" },
      { property: "og:description", content: "Find people thinking about similar or complementary questions." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

type FormState = { firstName: string; username: string; password: string; location: string };
const emptyForm: FormState = { firstName: "", username: "", password: "", location: "" };

function Index() {
  const [signupOpen, setSignupOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [welcome, setWelcome] = useState("");
  const signup = useServerFn(createAccount);
  const router = useRouter();

  const openSignup = () => {
    setError("");
    setSignupOpen(true);
  };

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const result = await signup({ data: form });
      setWelcome(result.firstName);
      setForm(emptyForm);
      await router.invalidate();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "We couldn't create your account.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="min-h-screen overflow-hidden bg-background text-foreground">
      <header className="relative z-20 mx-auto flex max-w-7xl items-center justify-between px-5 py-5 md:px-8">
        <a href="#top" className="font-display text-2xl font-semibold">The Fellowship</a>
        <nav className="hidden items-center gap-8 text-sm font-medium md:flex" aria-label="Main navigation">
          <a href="#how" className="text-muted-foreground transition-colors hover:text-foreground">How it works</a>
          <a href="#privacy" className="text-muted-foreground transition-colors hover:text-foreground">Privacy</a>
          <Button onClick={openSignup} size="lg">Join the network <ArrowRight /></Button>
        </nav>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open signup" onClick={openSignup}><Menu /></Button>
      </header>

      <section id="top" className="relative mx-auto grid min-h-[calc(100vh-80px)] max-w-7xl items-center gap-10 px-5 pb-16 pt-8 md:grid-cols-[1.05fr_.95fr] md:px-8 md:pb-24 md:pt-12">
        <div className="relative z-10 max-w-2xl">
          <p className="mb-6 font-mono text-xs font-medium uppercase tracking-[.18em] text-primary">Ideas that connect</p>
          <h1 className="font-display text-5xl font-semibold leading-[.96] md:text-7xl lg:text-8xl">Meet people by what they're thinking about.</h1>
          <p className="mt-7 max-w-xl text-lg leading-relaxed text-muted-foreground md:text-xl">Your best collaborator may already be exploring the same question—or holding the missing piece. The Fellowship finds that connection.</p>
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Button onClick={openSignup} size="xl">Create your account <ArrowRight /></Button>
            <span className="text-sm text-muted-foreground">Four fields. No biography required.</span>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-xl" aria-label="Example complementary match">
          <div className="absolute -left-10 top-20 hidden h-px w-24 bg-border lg:block" />
          <div className="match-panel overflow-hidden border border-border bg-card shadow-field">
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <span className="font-display text-2xl font-semibold">A promising connection</span>
              <span className="font-mono text-xs text-muted-foreground">FIT 0.91</span>
            </div>
            <div className="grid grid-cols-2">
              <div className="border-r border-border bg-peer px-5 py-7">
                <span className="font-mono text-[10px] uppercase text-peer-foreground">Them · Priya</span>
                <p className="mt-5 text-sm leading-relaxed">Diffusion models for protein-binding predictions</p>
              </div>
              <div className="bg-self px-5 py-7">
                <span className="font-mono text-[10px] uppercase text-primary">You · Sam</span>
                <p className="mt-5 text-sm leading-relaxed">SPR binding assays on small-molecule libraries</p>
              </div>
            </div>
            <div className="relative border-y border-border px-6 py-7 text-center">
              <span className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2 bg-complement px-3 py-1 font-mono text-[10px] uppercase text-complement-foreground">Complementary</span>
              <p className="font-display text-2xl italic">Meet. Learn. Collaborate.</p>
              <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">Together, you could test which compounds are worth taking into the lab.</p>
            </div>
            <div className="flex items-center justify-between px-6 py-5">
              <div className="flex -space-x-2"><span className="avatar bg-peer-strong">P</span><span className="avatar bg-primary">S</span></div>
              <span className="text-sm font-semibold text-primary">A conversation worth starting <ArrowRight className="ml-1 inline size-4" /></span>
            </div>
          </div>
        </div>
      </section>

      <section id="how" className="border-y border-border bg-surface py-20 md:py-28">
        <div className="mx-auto max-w-7xl px-5 md:px-8">
          <div className="grid gap-12 md:grid-cols-[.8fr_1.2fr]">
            <div><p className="font-mono text-xs uppercase tracking-[.18em] text-primary">How it works</p><h2 className="mt-4 font-display text-4xl font-semibold md:text-6xl">From chat history to human connection.</h2></div>
            <div className="divide-y divide-border border-y border-border">
              {[
                { number: "01", Icon: Upload, title: "Bring your conversations", copy: "Upload an export from ChatGPT or Claude. You choose what enters the process—nothing is pulled without you." },
                { number: "02", Icon: Sparkles, title: "We find the signal", copy: "Routine prompts and sensitive details are filtered out. Only the underlying ideas, questions, and skills become match signals." },
                { number: "03", Icon: Network, title: "Meet your intellectual neighbors", copy: "Discover people exploring the same frontier or bringing a capability that complements yours." },
              ].map(({ number, Icon: StepIcon, title, copy }) => {
                return <article key={number} className="grid grid-cols-[3rem_1fr] gap-4 py-8 md:grid-cols-[4rem_3rem_1fr] md:gap-6"><span className="font-mono text-xs text-muted-foreground">{number}</span><StepIcon className="hidden size-6 text-primary md:block" /><div><h3 className="font-display text-2xl font-semibold">{title}</h3><p className="mt-2 max-w-xl leading-relaxed text-muted-foreground">{copy}</p></div></article>;
              })}
            </div>
          </div>
        </div>
      </section>

      <section id="privacy" className="mx-auto max-w-7xl px-5 py-20 md:px-8 md:py-28">
        <div className="grid items-start gap-12 md:grid-cols-2 md:gap-20">
          <div className="sticky top-10"><LockKeyhole className="mb-6 size-8 text-primary" /><h2 className="font-display text-4xl font-semibold md:text-6xl">Your chats remain yours.</h2><p className="mt-6 max-w-lg text-lg leading-relaxed text-muted-foreground">They are processed to identify ideas—not exposed to build a public dossier. Raw conversation text is never shown to another member.</p></div>
          <div className="space-y-4">
            {[
              ["Opt-in by design", "You decide which exports to provide. There is no silent account connection or background collection."],
              ["Sensitive details held back", "Personal information and low-signal chatter are removed before ideas are used for matching."],
              ["Mutual consent", "A connection opens only when both people choose it. Until then, identity and contact details stay private."],
            ].map(([title, copy]) => <article key={title} className="border-l-2 border-primary py-3 pl-6"><h3 className="text-lg font-semibold">{title}</h3><p className="mt-2 leading-relaxed text-muted-foreground">{copy}</p></article>)}
          </div>
        </div>
      </section>

      <section className="bg-primary px-5 py-20 text-primary-foreground md:py-24">
        <div className="mx-auto flex max-w-4xl flex-col items-center text-center"><p className="font-mono text-xs uppercase tracking-[.18em] opacity-70">Your next connection is thinking now</p><h2 className="mt-5 font-display text-4xl font-semibold md:text-6xl">Join the people behind the ideas.</h2><Button variant="inverted" size="xl" className="mt-8" onClick={openSignup}>Create your account <ArrowRight /></Button></div>
      </section>

      <footer className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-8 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between md:px-8"><span className="font-display text-lg font-semibold text-foreground">The Fellowship</span><span>An AI-native discovery network for thoughtful people.</span></footer>

      {signupOpen && <div className="fixed inset-0 z-50 flex items-end justify-center bg-overlay p-0 backdrop-blur-sm md:items-center md:p-6" role="dialog" aria-modal="true" aria-labelledby="signup-title">
        <div className="relative max-h-[96vh] w-full max-w-lg overflow-y-auto rounded-t-xl bg-card p-6 shadow-modal md:rounded-lg md:p-9">
          <Button variant="ghost" size="icon" onClick={() => setSignupOpen(false)} className="absolute right-4 top-4" aria-label="Close signup"><X /></Button>
          {welcome ? <div className="py-10 text-center"><span className="mx-auto flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground"><Check /></span><h2 id="signup-title" className="mt-6 font-display text-4xl font-semibold">Welcome, {welcome}.</h2><p className="mt-3 text-muted-foreground">Your account is ready. You can start bringing in conversations and finding matches.</p><Button className="mt-8" size="lg" onClick={() => setSignupOpen(false)}>Continue</Button></div> : <>
            <p className="font-mono text-xs uppercase tracking-[.16em] text-primary">Join The Fellowship</p><h2 id="signup-title" className="mt-3 font-display text-4xl font-semibold">Start with the essentials.</h2><p className="mt-2 text-muted-foreground">No email, biography, affiliation, or professional profile required.</p>
            <form className="mt-8 space-y-5" onSubmit={submit}>
              <Field label="First name" id="firstName"><Input id="firstName" autoComplete="given-name" required maxLength={80} placeholder="Ada" value={form.firstName} onChange={(e) => setForm({ ...form, firstName: e.target.value })} /></Field>
              <Field label="Username" id="username" hint="3–30 lowercase letters, numbers, or underscores"><Input id="username" autoComplete="username" required minLength={3} maxLength={30} pattern="[a-z0-9_]+" placeholder="curious_mind" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value.toLowerCase() })} /></Field>
              <Field label="Password" id="password" hint="At least 8 characters"><Input id="password" type="password" autoComplete="new-password" required minLength={8} maxLength={72} placeholder="••••••••" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
              <Field label="Location" id="location" hint="City and region is enough"><Input id="location" autoComplete="address-level2" required maxLength={120} placeholder="Boston, MA" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} /></Field>
              {error && <p className="rounded-md bg-destructive-soft px-4 py-3 text-sm text-destructive" role="alert">{error}</p>}
              <p className="text-xs leading-relaxed text-muted-foreground">By creating an account, you acknowledge that only chats you choose to import may be processed to find matches. Raw chats are never shown to other members.</p>
              <Button type="submit" size="xl" className="w-full" disabled={pending}>{pending ? "Creating account…" : "Create account"}</Button>
            </form>
          </>}
        </div>
      </div>}
    </main>
  );
}

function Field({ label, id, hint, children }: { label: string; id: string; hint?: string; children: React.ReactNode }) {
  return <label htmlFor={id} className="block"><span className="mb-2 flex items-baseline justify-between text-sm font-semibold"><span>{label}</span>{hint && <span className="text-xs font-normal text-muted-foreground">{hint}</span>}</span>{children}</label>;
}
