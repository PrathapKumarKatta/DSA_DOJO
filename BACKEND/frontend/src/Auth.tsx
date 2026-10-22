import { useState } from "react";
import type { FormEvent } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCircle2,
  Circle,
  Command,
  Sparkles,
} from "lucide-react";
import { api, errorMessage, post, session } from "./api";
import { createDemo } from "./demo";
import type { User } from "./types";
import { Logo, Spinner } from "./ui";

export default function Auth({
  onLogin,
  notice,
}: {
  onLogin: (user: User) => void;
  notice?: string;
}) {
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState<"auth" | "demo" | null>(null);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy("auth");
    const form = new FormData(event.currentTarget);
    const credentials = {
      email: form.get("email"),
      password: form.get("password"),
    };
    try {
      if (register)
        await post("/auth/register", {
          ...credentials,
          full_name: form.get("full_name"),
        });
      const token = await post<{ access_token: string }>(
        "/auth/login",
        credentials,
      );
      session.set(token.access_token);
      onLogin(await api<User>("/users/me"));
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(null);
    }
  }

  async function demo() {
    setError("");
    setBusy("demo");
    try {
      onLogin(await createDemo());
    } catch (error) {
      session.clear();
      setError(errorMessage(error));
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-story">
        <Logo />
        <div className="auth-story-content">
          <span className="eyebrow">
            <span className="tiny-dot" /> A LITTLE MORE FLOW
          </span>
          <h1>
            Good work.
            <br />
            Great together<span>.</span>
          </h1>
          <p>
            Less juggling. More doing. A calmer place for your projects, your
            team, and the next big thing.
          </p>
          <div className="auth-preview" aria-hidden="true">
            <div className="preview-bar">
              <span>
                <Command size={15} /> Website launch
              </span>
              <span>•••</span>
            </div>
            <div className="preview-columns">
              <div>
                <small>
                  <Circle size={10} /> TO DO <b>3</b>
                </small>
                <div className="preview-card">
                  <em>DESIGN</em>
                  <strong>A fresh perspective</strong>
                  <span>Make space for a little magic.</span>
                  <div>
                    <i>AM</i>
                    <span>
                      Oct 24 <ArrowUpRight size={12} />
                    </span>
                  </div>
                </div>
              </div>
              <div>
                <small>
                  <span className="tiny-dot" /> IN PROGRESS <b>2</b>
                </small>
                <div className="preview-card raised">
                  <em className="orange">IN THE WORKS</em>
                  <strong>Bring the ideas to life</strong>
                  <span>Small steps. Real progress.</span>
                  <div>
                    <i>JK</i>
                    <span>
                      <Check size={12} /> 2 / 4
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div className="preview-success">
              <CheckCircle2 size={17} />
              <span>One step closer to something great.</span>
              <Sparkles size={15} />
            </div>
          </div>
        </div>
        <div className="auth-footer">
          <span>Made for the way you work.</span>
          <span>Thoughtfully simple.</span>
        </div>
      </section>
      <section className="auth-form-side">
        <span className="auth-corner">
          YOUR NEXT CHAPTER STARTS HERE <ArrowUpRight size={15} />
        </span>
        <div className="auth-form-wrap">
          <div className="auth-icon">
            <Sparkles size={23} />
          </div>
          <h2>{register ? "Make room for good work." : "Welcome back."}</h2>
          <p>
            {register
              ? "A fresh workspace. A world of possibilities."
              : "Pick up where you left off. Let’s make things happen."}
          </p>
          {notice && <div className="notice">{notice}</div>}
          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}
          <form onSubmit={submit} className="stack-form">
            {register && (
              <label>
                Full name
                <input
                  name="full_name"
                  autoComplete="name"
                  placeholder="Alex Morgan"
                  required
                  maxLength={120}
                />
              </label>
            )}
            <label>
              Email address
              <input
                name="email"
                type="email"
                autoComplete="email"
                placeholder="you@yourteam.com"
                required
                maxLength={320}
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
                minLength={register ? 10 : 1}
                maxLength={128}
                placeholder={
                  register ? "At least 10 characters" : "Enter your password"
                }
                required
              />
            </label>
            <button className="button primary auth-submit" disabled={!!busy}>
              {busy === "auth" ? <Spinner /> : null}
              {register ? "Create your account" : "Sign in to Taskflow"}
              <ArrowRight size={17} />
            </button>
          </form>
          <p className="auth-switch">
            {register ? "Already part of the flow?" : "New around here?"}{" "}
            <button
              className="text-button"
              onClick={() => {
                setRegister(!register);
                setError("");
              }}
              disabled={!!busy}
            >
              {register ? "Sign in" : "Create an account"}
            </button>
          </p>
          <div className="or-divider">
            <span />
            or take a look around
            <span />
          </div>
          <button
            className="button demo-button"
            onClick={demo}
            disabled={!!busy}
          >
            {busy === "demo" ? <Spinner /> : <Sparkles size={17} />}
            {busy === "demo"
              ? "Setting up your workspace…"
              : "Explore a live demo"}
            <ArrowUpRight size={16} />
          </button>
          <p className="demo-note">
            Your own demo workspace. Real tasks. No setup.
          </p>
        </div>
        <p className="auth-bottom">
          A little less busywork. A lot more progress.
        </p>
      </section>
    </main>
  );
}
