<!doctype html>
<html lang="si">

<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Vertex | Next-Gen Face Recognition</title>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet" />
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
  <style>
    body {
      font-family: "Poppins", sans-serif;
      color: #2b3452;
      background-color: #fcfcfd;
    }

    .modern-nav {
      background: rgba(255, 255, 255, 0.85);
      backdrop-filter: blur(15px);
      -webkit-backdrop-filter: blur(15px);
      border-bottom: 1px solid rgba(0, 0, 0, 0.05);
      padding: 15px 0;
      transition: all 0.3s ease;
    }

    .nav-link {
      color: #4a5568 !important;
      font-size: 0.95rem;
      transition: color 0.3s ease;
    }

    .nav-link:hover {
      color: #0d6efd !important;
    }

    .text-gradient {
      background: linear-gradient(135deg, #0d6efd, #00d2ff);
      background-clip: text;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .btn-gradient {
      background: linear-gradient(135deg, #0d6efd, #00d2ff);
      color: white;
      border: none;
      transition:
        transform 0.3s ease,
        box-shadow 0.3s ease;
    }

    .btn-gradient:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 20px rgba(13, 110, 253, 0.3);
      color: white;
    }

    .hero-section {
      min-height: 90vh;
      padding-top: 80px;
      background:
        radial-gradient(circle at top right,
          rgba(13, 110, 253, 0.05),
          transparent 40%),
        radial-gradient(circle at bottom left,
          rgba(0, 210, 255, 0.05),
          transparent 40%);
    }

    .hero-img {
      animation: float 6s ease-in-out infinite;
    }

    @keyframes float {
      0% {
        transform: translateY(0px);
      }

      50% {
        transform: translateY(-20px);
      }

      100% {
        transform: translateY(0px);
      }
    }

    .mt-n5 {
      margin-top: -3rem !important;
    }

    @media (min-width: 768px) {
      .border-end-md {
        border-right: 1px solid #e2e8f0;
      }
    }

    .bg-light-modern {
      background-color: #f8fafc;
    }

    .py-6 {
      padding-top: 100px;
      padding-bottom: 100px;
    }

    .service-card,
    .feature-card,
    .team-card {
      border: 1px solid rgba(0, 0, 0, 0.03);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.02);
      transition: all 0.3s ease;
    }

    .service-card:hover,
    .feature-card:hover,
    .team-card:hover {
      transform: translateY(-10px);
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.06);
    }

    .icon-box {
      width: 80px;
      height: 80px;
    }

    .team-img-wrapper {
      width: 130px;
      height: 130px;
      margin: 0 auto;
      overflow: hidden;
      border: 4px solid #fff;
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
    }

    .team-img-wrapper img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .pricing-card {
      transition: transform 0.3s ease;
      height: 100%;
    }

    .pricing-card:hover {
      transform: translateY(-10px);
    }

    .premium-card {
      background: linear-gradient(135deg, #1e293b, #0f172a);
      box-shadow: 0 20px 50px rgba(15, 23, 42, 0.2) !important;
      transform: scale(1.05);
      z-index: 2;
    }

    @media (max-width: 1199px) {
      .premium-card {
        transform: scale(1);
      }
    }

    .accordion-item {
      border: 1px solid rgba(0, 0, 0, 0.05);
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.01);
    }

    .accordion-button:not(.collapsed) {
      background-color: rgba(13, 110, 253, 0.05);
      color: #0d6efd;
    }

    .hover-white {
      transition: color 0.3s ease;
    }

    .hover-white:hover {
      color: white !important;
    }
  </style>
</head>

<body>
  <nav class="navbar navbar-expand-lg fixed-top modern-nav">
    <div class="container">
      <a class="navbar-brand fw-bold fs-3 brand-text" href="#">VERTEX<span class="text-primary">.</span></a>
      <button class="navbar-toggler border-0" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
        <i class="fa-solid fa-bars-staggered text-dark fs-4"></i>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav ms-auto fw-semibold align-items-center">
          <li class="nav-item"><a class="nav-link" href="#home">Home</a></li>
          <li class="nav-item">
            <a class="nav-link" href="#services">Services</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#features">Features</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#pricing">Pricing</a>
          </li>
          <li class="nav-item"><a class="nav-link" href="#team">Team</a></li>
          <li class="nav-item ms-lg-3 mt-2 mt-lg-0">
            <a
              class="btn btn-gradient rounded-pill px-4 py-2 w-100"
              href="#pricing">Get Started</a>
          </li>
        </ul>
      </div>
    </div>
  </nav>

  <section id="home" class="hero-section d-flex align-items-center">
    <div class="container">
      <div class="row align-items-center">
        <div class="col-lg-6 hero-text text-center text-lg-start">
          <span
            class="badge bg-primary-subtle text-primary rounded-pill px-3 py-2 mb-3 fw-bold">AI Powered System</span>
          <h1 class="display-4 fw-bold mb-4">
            Smart Attendance for <br /><span class="text-gradient">Modern Workplaces</span>
          </h1>
          <p class="lead text-secondary mb-4">
            Replace manual logging with millisecond-accurate facial
            recognition. Easily installable standalone EXE for Windows.
          </p>
          <div
            class="d-flex gap-3 justify-content-center justify-content-lg-start flex-wrap">
            <a
              href="#pricing"
              class="btn btn-gradient rounded-pill px-4 py-3 fw-bold shadow-lg">View Plans</a>
            <a
              href="#download"
              class="btn btn-outline-dark rounded-pill px-4 py-3 fw-bold"><i class="fa-solid fa-download me-2"></i>Download Free</a>
          </div>
        </div>
        <div class="col-lg-6 mt-5 mt-lg-0 text-center">
          <img
            src="https://images.unsplash.com/photo-1550751827-4bd374c3f58b?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
            alt="Face Recognition"
            class="img-fluid hero-img shadow-lg rounded-4" />
        </div>
      </div>
    </div>
  </section>

  <section class="container mt-n5 position-relative stats-section z-2">
    <div
      class="row bg-white rounded-4 shadow-sm p-4 text-center mx-2 mx-md-0">
      <div class="col-md-4 border-end-md mb-3 mb-md-0">
        <h2 class="fw-bold text-primary display-5">99.9%</h2>
        <p class="text-muted fw-semibold mb-0">Accuracy</p>
      </div>
      <div class="col-md-4 border-end-md mb-3 mb-md-0">
        <h2 class="fw-bold text-primary display-5">&lt;1s</h2>
        <p class="text-muted fw-semibold mb-0">Detection Time</p>
      </div>
      <div class="col-md-4">
        <h2 class="fw-bold text-primary display-5">100%</h2>
        <p class="text-muted fw-semibold mb-0">Offline Capability</p>
      </div>
    </div>
  </section>

  <section id="services" class="py-6 bg-light-modern">
    <div class="container">
      <div class="text-center mb-5">
        <h2 class="fw-bold">
          Seamless <span class="text-primary">Integration</span>
        </h2>
        <p class="text-muted">Designed for efficiency and ease of use.</p>
      </div>
      <div class="row g-4">
        <div class="col-md-4">
          <div class="service-card p-5 bg-white rounded-4 text-center h-100">
            <div
              class="icon-box bg-primary-subtle text-primary rounded-circle d-inline-flex justify-content-center align-items-center mb-4">
              <i class="fa-solid fa-desktop fa-2x"></i>
            </div>
            <h4 class="fw-bold">Easy Deployment</h4>
            <p class="text-muted">
              Single EXE file installation. No complex server setups needed
              for your local PC.
            </p>
          </div>
        </div>
        <div class="col-md-4">
          <div class="service-card p-5 bg-white rounded-4 text-center h-100">
            <div
              class="icon-box bg-success-subtle text-success rounded-circle d-inline-flex justify-content-center align-items-center mb-4">
              <i class="fa-solid fa-expand fa-2x"></i>
            </div>
            <h4 class="fw-bold">AI Recognition</h4>
            <p class="text-muted">
              Trained with advanced Python algorithms to detect faces even
              with minor changes.
            </p>
          </div>
        </div>
        <div class="col-md-4">
          <div class="service-card p-5 bg-white rounded-4 text-center h-100">
            <div
              class="icon-box bg-warning-subtle text-warning rounded-circle d-inline-flex justify-content-center align-items-center mb-4">
              <i class="fa-solid fa-file-invoice fa-2x"></i>
            </div>
            <h4 class="fw-bold">Smart Reporting</h4>
            <p class="text-muted">
              Generate professional PDF and Excel attendance sheets
              automatically.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section id="features" class="py-6">
    <div class="container">
      <div class="text-center mb-5">
        <h2 class="fw-bold">
          Why Choose <span class="text-gradient">Vertex AI</span>
        </h2>
        <p class="text-muted">
          Advanced security capabilities matching modern enterprise demands.
        </p>
      </div>
      <div class="row g-4">
        <div class="col-md-6 col-lg-4">
          <div class="feature-card p-4 bg-white rounded-4 h-100">
            <div class="d-flex align-items-center mb-3">
              <i class="fa-solid fa-shield-halved text-primary fs-3 me-3"></i>
              <h5 class="fw-bold mb-0">Secure Local DB</h5>
            </div>
            <p class="text-muted mb-0">
              Your biometric face data is encrypted and saved locally in MySQL
              with high security protocols.
            </p>
          </div>
        </div>
        <div class="col-md-6 col-lg-4">
          <div class="feature-card p-4 bg-white rounded-4 h-100">
            <div class="d-flex align-items-center mb-3">
              <i
                class="fa-solid fa-cloud-arrow-up text-primary fs-3 me-3"></i>
              <h5 class="fw-bold mb-0">Optional Cloud Sync</h5>
            </div>
            <p class="text-muted mb-0">
              Sync daily branch logs automatically into an online central
              management system interface.
            </p>
          </div>
        </div>
        <div class="col-md-6 col-lg-4">
          <div class="feature-card p-4 bg-white rounded-4 h-100">
            <div class="d-flex align-items-center mb-3">
              <i class="fa-solid fa-user-plus text-primary fs-3 me-3"></i>
              <h5 class="fw-bold mb-0">Fast Registration</h5>
            </div>
            <p class="text-muted mb-0">
              Register any user within seconds using just a basic standard
              webcam preview setup.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section id="pricing" class="py-6 bg-light-modern">
    <div class="container">
      <div class="text-center mb-5">
        <h2 class="fw-bold">
          Simple, <span class="text-primary">Transparent Pricing</span>
        </h2>
      </div>
      <div class="row g-4 align-items-center justify-content-center">

        <div class="col-xl-3 col-lg-6 col-md-6">
          <div class="pricing-card p-5 bg-white rounded-4 border">
            <h5 class="fw-bold text-muted mb-4">FREE</h5>
            <h2 class="display-5 fw-bold mb-4">
              $0.00<span class="fs-6 text-muted fw-normal">/mo</span>
            </h2>
            <ul class="list-unstyled mb-4">
              <li class="mb-3">
                <i class="fa-solid fa-check-circle text-primary me-2"></i> Up
                to 10 Staff
              </li>
              <li class="mb-3">
                <i class="fa-solid fa-check-circle text-primary me-2"></i>
                Basic Local Reports
              </li>
              <li class="mb-3">
                <i class="fa-solid fa-check-circle text-primary me-2"></i>
                Community Support
              </li>
            </ul>
            <a
              id="download"
              href="#"
              class="btn btn-outline-primary rounded-pill w-100 py-2 fw-bold"><i class="fa-solid fa-download me-2"></i>Download App</a>
          </div>
        </div>

        <div class="col-xl-3 col-lg-6 col-md-6">
          <div class="pricing-card p-5 bg-white rounded-4 border">
            <h5 class="fw-bold text-muted mb-4">BASIC</h5>
            <h2 class="display-5 fw-bold mb-4">
              $15.00<span class="fs-6 text-muted fw-normal">/mo</span>
            </h2>
            <ul class="list-unstyled mb-4">
              <li class="mb-3">
                <i class="fa-solid fa-check-circle text-primary me-2"></i> Up
                to 50 Staff
              </li>
              <li class="mb-3">
                <i class="fa-solid fa-check-circle text-primary me-2"></i>
                Standard Reports
              </li>
              <li class="mb-3">
                <i class="fa-solid fa-check-circle text-primary me-2"></i>
                Email Support
              </li>
            </ul>
            <a
              href="#contact"
              class="btn btn-outline-dark rounded-pill w-100 py-2 fw-bold">Select Plan</a>
          </div>
        </div>

        <div class="col-xl-3 col-lg-6 col-md-6">
          <div
            class="pricing-card p-5 rounded-4 shadow-lg premium-card text-white position-relative">
            <span
              class="badge bg-warning text-dark position-absolute top-0 start-50 translate-middle rounded-pill px-3 py-2 fw-bold">MOST POPULAR</span>
            <h5 class="fw-bold text-white-50 mb-4">PRO</h5>
            <h2 class="display-5 fw-bold mb-4">
              $25.00<span class="fs-6 text-white-50 fw-normal">/mo</span>
            </h2>
            <ul class="list-unstyled mb-4">
              <li class="mb-3">
                <i class="fa-solid fa-check-circle text-warning me-2"></i> Up
                to 200 Staff
              </li>
              <li class="mb-3">
                <i class="fa-solid fa-check-circle text-warning me-2"></i>
                Advanced Analytics
              </li>
              <li class="mb-3">
                <i class="fa-solid fa-check-circle text-warning me-2"></i>
                Priority 24/7 Support
              </li>
            </ul>
            <a
              href="#contact"
              class="btn btn-light rounded-pill w-100 py-2 fw-bold text-primary">Select Pro</a>
          </div>
        </div>

        <div class="col-xl-3 col-lg-6 col-md-6">
          <div class="pricing-card p-5 bg-white rounded-4 border">
            <h5 class="fw-bold text-muted mb-4">ENTERPRISE</h5>
            <h2 class="display-5 fw-bold mb-4">Custom</h2>
            <ul class="list-unstyled mb-4">
              <li class="mb-3">
                <i class="fa-solid fa-check-circle text-primary me-2"></i>
                Unlimited Staff
              </li>
              <li class="mb-3">
                <i class="fa-solid fa-check-circle text-primary me-2"></i>
                Cloud Sync Options
              </li>
              <li class="mb-3">
                <i class="fa-solid fa-check-circle text-primary me-2"></i>
                On-site Setup
              </li>
            </ul>
            <a
              href="#contact"
              class="btn btn-outline-dark rounded-pill w-100 py-2 fw-bold">Contact Sales</a>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section id="team" class="py-6">
    <div class="container">
      <div class="text-center mb-5">
        <h2 class="fw-bold">
          Our <span class="text-primary">Leadership Team</span>
        </h2>
        <p class="text-muted">
          The experts behind Vertex engineering innovation.
        </p>
      </div>
      <div class="row g-4 justify-content-center">
        <div class="col-md-6 col-lg-4 text-center">
          <div class="team-card p-4 bg-white rounded-4 h-100">
            <div class="team-img-wrapper rounded-circle mb-3">
              <img
                src="assects/img/images.png"
                alt="CEO Vertex" />
            </div>
            <h5 class="fw-bold mb-1">Chathuranga Pallewela </h5>
            <p class="text-primary small fw-semibold mb-3">
              Chief Executive Officer
            </p>
            <p class="text-muted small">
              Experienced tech visionary leading company product strategy and
              partnerships.
            </p>
            <div class="d-flex justify-content-center gap-2">
              <a href="#" class="text-secondary hover-primary"><i class="fa-brands fa-linkedin fs-5"></i></a>
            </div>
          </div>
        </div>
        <div class="col-md-6 col-lg-4 text-center">
          <div class="team-card p-4 bg-white rounded-4 h-100">
            <div class="team-img-wrapper rounded-circle mb-3">
              <img
                src="assects/img/photo_2026-06-10_19-29-53.jpg"
                alt="CTO Vertex" />
            </div>
            <h5 class="fw-bold mb-1">Nadhun Warnakulasooriya</h5>
            <p class="text-primary small fw-semibold mb-3">
              Chief Technology Officer
            </p>
            <p class="text-muted small">
              Lead AI Systems Architect specialized in Computer Vision
              algorithms & Python frameworks.
            </p>
            <div class="d-flex justify-content-center gap-2">
              <a href="#" class="text-secondary hover-primary"><i class="fa-brands fa-linkedin fs-5"></i></a>
            </div>
          </div>
        </div>
        <div class="col-md-6 col-lg-4 text-center">
          <div class="team-card p-4 bg-white rounded-4 h-100">
            <div class="team-img-wrapper rounded-circle mb-3">
              <img
                src="assects/img/20260610_192029 (1).jpg"
                alt="Lead Engineer" />
            </div>
            <h5 class="fw-bold mb-1">Sameera Ayeshmantha</h5>
            <p class="text-primary small fw-semibold mb-3">
              Chief Technology Officer
            </p>
            <p class="text-muted small">
              Specialist in software optimization, local database compiling,
              and secure local PC standalone deployment.
            </p>
            <div class="d-flex justify-content-center gap-2">
              <a href="#" class="text-secondary hover-primary"><i class="fa-brands fa-linkedin fs-5"></i></a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="py-6 bg-light-modern">
    <div class="container" style="max-width: 800px">
      <div class="text-center mb-5">
        <h2 class="fw-bold">
          Frequently Asked <span class="text-primary">Questions</span>
        </h2>
        <p class="text-muted">Clear answers to your technical queries.</p>
      </div>
      <div class="accordion accordion-flush" id="faqAccordion">
        <div class="accordion-item rounded-3 mb-3 overflow-hidden">
          <h2 class="accordion-header">
            <button
              class="accordion-button fw-bold"
              type="button"
              data-bs-toggle="collapse"
              data-bs-target="#faq1"
              aria-expanded="true"
              aria-controls="faq1">
              Does the system require an active internet connection to mark
              attendance?
            </button>
          </h2>
          <div
            id="faq1"
            class="accordion-collapse collapse show"
            data-bs-parent="#faqAccordion">
            <div class="accordion-body text-muted">
              No, the software runs 100% offline. All facial recognition data
              processing and database entries are handled inside your local
              Windows PC architecture.
            </div>
          </div>
        </div>
        <div class="accordion-item rounded-3 mb-3 overflow-hidden">
          <h2 class="accordion-header">
            <button
              class="accordion-button collapsed fw-bold"
              type="button"
              data-bs-toggle="collapse"
              data-bs-target="#faq2"
              aria-expanded="false"
              aria-controls="faq2">
              What hardware cameras are compatible with the software?
            </button>
          </h2>
          <div
            id="faq2"
            class="accordion-collapse collapse"
            data-bs-parent="#faqAccordion">
            <div class="accordion-body text-muted">
              Any standard USB External Webcam or standard built-in Laptop HD
              Camera can be seamlessly integrated with the executable software
              setup.
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <footer id="contact" class="footer-modern bg-dark text-white pt-5 pb-3">
    <div class="container">
      <div class="row g-4 mb-4">
        <div class="col-lg-4 col-md-12 mb-4 mb-lg-0">
          <h3 class="fw-bold brand-text mb-3">
            VERTEX<span class="text-primary">.</span>
          </h3>
          <p class="text-white-50">
            Empowering modern workplaces with next-generation AI solutions.
            Built for speed, accuracy, and reliability.
          </p>
          <div class="social-links mt-4">
            <a href="#" class="text-white-50 me-3 fs-5 hover-white"><i class="fa-brands fa-facebook"></i></a>
            <a href="#" class="text-white-50 me-3 fs-5 hover-white"><i class="fa-brands fa-linkedin"></i></a>
            <a href="#" class="text-white-50 me-3 fs-5 hover-white"><i class="fa-brands fa-twitter"></i></a>
            <a href="#" class="text-white-50 fs-5 hover-white"><i class="fa-brands fa-github"></i></a>
          </div>
        </div>

        <div class="col-lg-3 col-md-6 mb-4 mb-lg-0">
          <h5 class="fw-bold mb-4">Company</h5>
          <ul class="list-unstyled">
            <li class="mb-2">
              <a
                href="#about"
                class="text-white-50 text-decoration-none hover-white">About Us</a>
            </li>
            <li class="mb-2">
              <a
                href="#careers"
                class="text-white-50 text-decoration-none hover-white">Careers</a>
            </li>
            <li class="mb-2">
              <a
                href="#privacy"
                class="text-white-50 text-decoration-none hover-white">Privacy Policy</a>
            </li>
            <li class="mb-2">
              <a
                href="#terms"
                class="text-white-50 text-decoration-none hover-white">Terms of Service</a>
            </li>
            <li class="mb-2">
              <a
                href="#support"
                class="text-white-50 text-decoration-none hover-white">Help & Support</a>
            </li>
          </ul>
        </div>

        <div class="col-lg-5 col-md-6">
          <form
            class="bg-white p-4 rounded-4 shadow-sm text-dark"
            action="contact_process.php"
            method="POST">
            <h5 class="fw-bold mb-3">Ready to upgrade your system?</h5>
            <div class="row g-2">
              <div class="col-md-6">
                <input
                  type="text"
                  class="form-control rounded-3"
                  name="name"
                  placeholder="Name"
                  required />
              </div>
              <div class="col-md-6">
                <input
                  type="email"
                  class="form-control rounded-3"
                  name="email"
                  placeholder="Email"
                  required />
              </div>
              <div class="col-12">
                <textarea
                  class="form-control rounded-3"
                  name="message"
                  rows="2"
                  placeholder="Message"
                  required></textarea>
              </div>
              <div class="col-12 mt-3">
                <button
                  type="submit"
                  class="btn btn-gradient rounded-pill w-100 py-2 fw-bold">
                  Send Message
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div class="border-top border-secondary pt-3 mt-4 text-center">
        <p class="text-white-50 mb-0 small">
          &copy; 2026 Vertex. All Rights Reserved.
        </p>
      </div>
    </div>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>

  <script>
    const navLinks = document.querySelectorAll(
      ".nav-item:not(.dropdown) .nav-link",
    );
    const menuToggle = document.getElementById("navbarNav");
    const bsCollapse = new bootstrap.Collapse(menuToggle, {
      toggle: false
    });
    navLinks.forEach((l) => {
      l.addEventListener("click", () => {
        if (menuToggle.classList.contains("show")) {
          bsCollapse.toggle();
        }
      });
    });
  </script>
</body>

</html>