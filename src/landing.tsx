import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Camera,
  Check,
  Folder,
  Image,
  Play,
  Server,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Footer, Wordmark } from "./shared";

export function Landing() {
  return (
    <div className="landing">
      <header className="site-header">
        <Wordmark />
        <nav aria-label="Main navigation">
          <a href="#how">How it works</a>
          <a href="#setup">The setup</a>
          <a className="nav-app" href="/app">
            Open Plunk <ArrowUpRight size={16} />
          </a>
        </nav>
      </header>
      <main>
        <section className="hero">
          <div className="hero-copy">
            <div className="pill">
              <span className="status-dot" /> SMALL TOOL. BIG EXHALE.
            </div>
            <h1>
              Your camera.
              <br />
              Your folders.
              <br />
              <span>Plunk.</span>
              <svg
                className="word-underline"
                viewBox="0 0 270 22"
                aria-hidden="true"
              >
                <path d="M3 13Q120-4 263 9M22 20Q156 6 241 16" />
              </svg>
            </h1>
            <p>
              Take a picture. Give it a name. Pick where it goes.
              <br className="desktop-break" /> Straight to your server, ready
              for whatever comes next.
            </p>
            <div className="hero-actions">
              <a className="button primary" href="#setup">
                Set up Plunk <ArrowUpRight size={19} />
              </a>
              <a className="demo-link" href="#demo">
                <span>
                  <Play size={13} fill="currentColor" />
                </span>
                See it work
              </a>
            </div>
            <div className="hero-note">
              <span>No middleman.</span>
              <span>No camera-roll archaeology.</span>
            </div>
          </div>
          <div
            className="hero-stage"
            role="img"
            aria-label="A picture named the-plan.jpg arriving in a project folder"
          >
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <span className="stage-label label-a">
              a little out in the world
            </span>
            <div className="photo-tile">
              <div className="whiteboard">
                <span className="board-title">the next big thing</span>
                <div className="board-flow">
                  <span>an idea</span>
                  <ArrowRight size={23} />
                  <span>
                    make it
                    <br />
                    real
                  </span>
                </div>
                <div className="board-scribble">
                  less friction.
                  <br />
                  <b>more doing.</b>
                </div>
                <div className="board-star">✳</div>
              </div>
              <div className="photo-caption">
                <Image size={16} />
                <span>the-plan.jpg</span>
                <span className="caption-dot" />
              </div>
            </div>
            <svg
              className="drop-arrow"
              viewBox="0 0 110 150"
              aria-hidden="true"
            >
              <path d="M27 6C95 18 19 90 79 119M51 110l31 15 8-33" />
            </svg>
            <div className="folder-illustration">
              <div className="folder-tab" />
              <div className="folder-back" />
              <div className="folder-front">
                <Folder size={32} strokeWidth={1.5} />
                <span>Projects / next-big-thing</span>
                <span className="folder-check">
                  <Check size={19} />
                </span>
              </div>
            </div>
            <div className="arrival">
              <span>
                <Check size={16} />
              </span>
              Right where it belongs.
            </div>
            <span className="stage-label label-b">a little closer to done</span>
            <span className="spark spark-one">✳</span>
            <span className="spark spark-two">+</span>
          </div>
        </section>
        <section className="workflow-strip" id="how">
          <span>THREE LITTLE STEPS.</span>
          <div>
            <Camera /> Pic <ArrowRight /> <span>Name</span> <ArrowRight />{" "}
            <Folder /> Location<span className="workflow-period">.</span>
          </div>
          <a href="/app">
            That’s the whole thing <ArrowDown size={16} />
          </a>
        </section>
        <section className="context-section">
          <div className="section-heading">
            <span className="eyebrow">BRING THE OUTSIDE IN</span>
            <h2>
              Your context isn’t all
              <br />
              on your computer.
            </h2>
            <p>
              It’s on the whiteboard. Under the desk.
              <br />
              Scribbled on the back of something.
            </p>
          </div>
          <div className="use-cases">
            <article className="use-case">
              <div className="use-art board-art">
                <div className="mini-board">
                  <span>what if…</span>
                  <div>idea → sketch → build</div>
                  <b>start here ↗</b>
                </div>
              </div>
              <span className="case-number">01 / THE BIG PICTURE</span>
              <h3>The whiteboard worth keeping.</h3>
              <p>Put the plan next to the project.</p>
            </article>
            <article className="use-case">
              <div className="use-art sketch-art">
                <div className="sketch-paper">
                  <span>one small idea</span>
                  <div className="sketch-box">
                    <i />
                    <i />
                    <i />
                  </div>
                  <b>keep it simple ↗</b>
                </div>
              </div>
              <span className="case-number">02 / THE ROUGH IDEA</span>
              <h3>The sketch that says it better.</h3>
              <p>Less explaining. More showing.</p>
            </article>
            <article className="use-case">
              <div className="use-art hardware-art">
                <div className="circuit">
                  <span />
                  <span />
                  <span />
                  <div className="chip">
                    HELLO
                    <br />
                    WORLD
                  </div>
                  <i />
                  <i />
                </div>
              </div>
              <span className="case-number">03 / THE ACTUAL THING</span>
              <h3>The setup in front of you.</h3>
              <p>Give your model something real to look at.</p>
            </article>
          </div>
        </section>
        <section className="model-section">
          <span className="model-symbol">
            <Sparkles size={32} />
          </span>
          <div>
            <span className="eyebrow">FOR THE “HERE, LOOK” MOMENTS</span>
            <h2>
              Real-world context.
              <br />
              Meet your models.
            </h2>
            <p>
              Plunk puts pictures in your project folders. You choose how your
              model tooling uses them. No special integration. Just a file,
              right where you need it.
            </p>
          </div>
          <div className="code-receipt">
            <span>
              <span className="status-dot" /> next-big-thing
            </span>
            <div>
              ├─ README.md
              <br />
              ├─ src/
              <br />
              └─{" "}
              <strong>
                the-plan.jpg <Check size={15} />
              </strong>
            </div>
            <small>That’s a lot easier to explain now.</small>
          </div>
        </section>
        <section className="demo-section" id="demo">
          <div className="section-heading">
            <span className="eyebrow">LESS TALK. MORE PLUNK.</span>
            <h2>
              From “here, look”
              <br />
              to right there.
            </h2>
            <p>A real local upload, from the app to a Linux folder.</p>
          </div>
          <div className="demo-grid">
            <figure>
              <img
                src="/launch/app-name.png"
                alt="Plunk naming screen with a selected test whiteboard image"
                loading="lazy"
              />
              <figcaption>01 · Give the picture a useful name.</figcaption>
            </figure>
            <figure>
              <img
                src="/launch/app-location.png"
                alt="Plunk browsing the Linux listener’s project folders"
                loading="lazy"
              />
              <figcaption>02 · Choose its home.</figcaption>
            </figure>
            <figure>
              <img
                src="/launch/app-success.png"
                alt="Plunk receipt confirming the JPEG was saved"
                loading="lazy"
              />
              <figcaption>03 · Plunked. Confirmed by the listener.</figcaption>
            </figure>
          </div>
          <details className="demo-video">
            <summary>
              Watch the actual upload <Play size={14} />
            </summary>
            <video
              controls
              playsInline
              preload="none"
              poster="/launch/app-name.png"
              aria-label="Screen recording of a real Plunk upload to a Linux listener"
            >
              <source src="/launch/plunk-demo.mp4" type="video/mp4" />
              <track
                kind="captions"
                src="/launch/demo.vtt"
                srcLang="en"
                label="English"
                default
              />
            </video>
          </details>
          <p className="demo-caption">
            Desktop browser at phone size · Linux listener in WSL · test image.
            Physical iPhone camera and remote-server verification are still
            pending.
          </p>
        </section>
        <section className="setup-section" id="setup">
          <div>
            <span className="eyebrow">ONCE NOW. EASY LATER.</span>
            <h2>
              A little setup.
              <br />A lot less sending
              <br />
              things to yourself.
            </h2>
            <p>
              Bring a Linux server and an HTTPS address.
              <br />
              We’ll bring the little orange button.
            </p>
            <a className="button primary" href="/setup.html">
              Read the setup guide <ArrowUpRight size={19} />
            </a>
          </div>
          <ol className="setup-list">
            <li>
              <span>01</span>
              <div>
                <h3>
                  <Server size={20} /> Start your listener.
                </h3>
                <p>
                  Run Plunk on Linux. Choose which folders it can see and write
                  to.
                </p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <h3>
                  <ShieldCheck size={20} /> Connect your phone.
                </h3>
                <p>
                  Save the HTTPS address and any required token or password.
                  Local or remote, same flow.
                </p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <h3>
                  <Camera size={20} /> Make yourself at home.
                </h3>
                <p>
                  Open Plunk in Safari and add it to your Home Screen. Your next
                  picture has somewhere to go.
                </p>
              </div>
            </li>
          </ol>
        </section>
        <section className="closing">
          <img src="/brand/icon.svg" alt="" />
          <h2>
            Less sending things to yourself.
            <br />
            <span>More doing things with them.</span>
          </h2>
          <a className="button dark" href="/app">
            Let’s Plunk <ArrowUpRight size={20} />
          </a>
          <p>Your camera. Your folders. Plunk.</p>
        </section>
      </main>
      <Footer />
    </div>
  );
}
