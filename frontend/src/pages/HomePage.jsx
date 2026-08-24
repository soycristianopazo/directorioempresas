import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Building2,
  Cpu,
  Factory,
  FileCheck2,
  Handshake,
  HardHat,
  Landmark,
  Layers,
  Leaf,
  Package,
  Search,
  ShieldCheck,
  Sparkles,
  Truck,
  Users,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/context/AuthContext';
import logo from '@/assets/logo.png';
import logoIcon from '@/assets/logo-icon.png';

const CATEGORIES = [
  { label: 'Minería', icon: Factory },
  { label: 'Construcción', icon: HardHat },
  { label: 'Transporte y logística', icon: Truck },
  { label: 'Ingeniería', icon: Cpu },
  { label: 'Servicios industriales', icon: Package },
  { label: 'Energía', icon: Zap },
  { label: 'Retail', icon: Building2 },
  { label: 'Sector público', icon: Landmark },
];

const SUPPLIER_BENEFITS = [
  {
    icon: Search,
    title: 'Que te encuentren, no que te busquen',
    description:
      'Publica un perfil verificado por rubro, industria y territorio. Los compradores llegan a ti cuando buscan exactamente lo que ofreces.',
  },
  {
    icon: FileCheck2,
    title: 'Cotiza sin cadenas de correos',
    description:
      'Recibe requerimientos con alcance, plazo y condiciones claras desde el primer mensaje. Cotiza, ajusta y adjudica en un solo lugar.',
  },
  {
    icon: ShieldCheck,
    title: 'La confianza se ve, no se promete',
    description:
      'Certificaciones, referencias y años de experiencia quedan en tu perfil como evidencia — no como una frase más en una presentación.',
  },
];

const BUYER_BENEFITS = [
  {
    icon: Layers,
    title: 'Un mercado, no una libreta de contactos',
    description:
      'Compara proveedores reales por especialidad, cobertura territorial y experiencia comprobada en tu industria, no solo por quién conoces.',
  },
  {
    icon: Handshake,
    title: 'Del requerimiento a la adjudicación',
    description:
      'Publica lo que necesitas, recibe cotizaciones comparables lado a lado y cierra el proceso con trazabilidad completa.',
  },
  {
    icon: Users,
    title: 'Todo tu equipo, un solo perfil de empresa',
    description:
      'Invita a compras, operaciones y finanzas con roles y permisos claros. Nadie parte de cero ni duplica gestiones.',
  },
];

const STEPS = [
  {
    number: '01',
    title: 'Crea el perfil de tu empresa',
    description: 'Una cuenta, un RUT verificado. Indica si vendes, compras o ambas — puedes cambiarlo cuando quieras.',
  },
  {
    number: '02',
    title: 'Publica lo que ofreces o necesitas',
    description: 'Clasifica tu oferta o levanta un requerimiento con el detalle que un proveedor o comprador necesita para responder en serio.',
  },
  {
    number: '03',
    title: 'Conecta, cotiza y adjudica',
    description: 'El match ocurre por rubro, industria y territorio. La conversación y la cotización quedan documentadas de punta a punta.',
  },
];

export default function HomePage() {
  const { isAuthenticated, loading } = useAuth();

  return (
    <div className="flex min-h-dvh flex-col overflow-x-clip bg-background">
      <Helmet>
        <title>Directorio de Empresas · Conectamos proveedores y compradores en Chile</title>
        <meta
          name="description"
          content="El punto de encuentro entre empresas proveedoras y compradoras en Chile. Publica tu empresa, cotiza y adjudica en un solo lugar — y ayuda a mover la economía local."
        />
      </Helmet>

      <SiteHeader isAuthenticated={isAuthenticated} loading={loading} />

      <main className="flex-1">
        <Hero />
        <MissionBand />
        <AudienceSection />
        <HowItWorks />
        <CategoriesSection />
        <FinalCta />
      </main>

      <SiteFooter />
    </div>
  );
}

function SiteHeader({ isAuthenticated, loading }) {
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2">
          <img src={logo} alt="Directorio de Empresas" className="h-8 w-auto sm:h-9" />
        </Link>

        <nav className="hidden items-center gap-8 text-sm font-medium text-muted-foreground md:flex">
          <a href="#como-funciona" className="transition-colors hover:text-foreground">
            Cómo funciona
          </a>
          <a href="#categorias" className="transition-colors hover:text-foreground">
            Categorías
          </a>
          <a href="#mision" className="transition-colors hover:text-foreground">
            Nuestra misión
          </a>
        </nav>

        <div className="flex items-center gap-2">
          {loading ? null : isAuthenticated ? (
            <Button asChild size="sm">
              <Link to="/dashboard">Ir al panel</Link>
            </Button>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
                <Link to="/login">Iniciar sesión</Link>
              </Button>
              <Button asChild size="sm">
                <Link to="/register">
                  Crear cuenta gratis
                </Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative">
      {/* Composición de manchas orgánicas, en eco al motivo del logo — decorativa. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-24 right-[-10%] size-[32rem] rounded-full bg-brand-lime/25 blur-3xl" />
        <div className="absolute top-40 left-[-15%] size-[28rem] rounded-full bg-brand-teal/20 blur-3xl" />
        <div className="absolute top-10 right-[20%] size-64 rounded-full bg-brand-sky/40 blur-2xl" />
      </div>

      <div className="relative mx-auto max-w-7xl px-6 pb-20 pt-16 sm:pb-28 sm:pt-24">
        <div className="mx-auto max-w-3xl text-center">
          <Badge variant="brand" className="gap-1.5 py-1.5">
            <Sparkles className="size-3.5" />
            Marketplace B2B chileno
          </Badge>

          <h1 className="mt-6 text-4xl font-bold tracking-tight text-foreground sm:text-5xl md:text-6xl">
            Cada empresa que se conecta bien{' '}
            <span className="bg-gradient-to-r from-brand-teal to-brand-olive bg-clip-text text-transparent">
              hace crecer a la que sigue
            </span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            Directorio de Empresas es el lugar donde proveedores ganan visibilidad real y compradores
            encuentran con quién trabajar — sin cadenas de WhatsApp ni licitaciones a ciegas. Cada
            match bien hecho fortalece un poco más la economía de todos.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button asChild size="lg" className="w-full gap-2 sm:w-auto">
              <Link to="/register">
                Registrar mi empresa
                <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="w-full sm:w-auto">
              <a href="#como-funciona">Ver cómo funciona</a>
            </Button>
          </div>

          <p className="mt-5 text-sm text-muted-foreground">
            Sin costo de publicación. Verificamos tu RUT, no tu billetera.
          </p>
        </div>
      </div>
    </section>
  );
}

function MissionBand() {
  const pillars = [
    {
      icon: ShieldCheck,
      title: 'Formaliza',
      description: 'Perfiles con RUT verificado, certificaciones y referencias reales, no solo un logo y un teléfono.',
    },
    {
      icon: Search,
      title: 'Visibiliza',
      description: 'Empresas que hoy dependen del boca a boca ganan un canal directo hacia compradores que las buscan.',
    },
    {
      icon: Handshake,
      title: 'Conecta',
      description: 'Menos fricción entre quien necesita y quien puede resolver, más tiempo dedicado a lo que importa.',
    },
  ];

  return (
    <section id="mision" className="relative overflow-hidden bg-brand-teal-dark py-20 text-white sm:py-24">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div className="absolute -left-20 top-1/2 size-96 -translate-y-1/2 rounded-full bg-brand-lime/10 blur-3xl" />
        <div className="absolute -right-16 bottom-[-6rem] size-80 rounded-full bg-brand-sky/10 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-5xl px-6 text-center">
        <p className="text-sm font-semibold uppercase tracking-wider text-brand-lime">Por qué existimos</p>
        <blockquote className="mx-auto mt-4 max-w-3xl text-2xl font-semibold leading-snug tracking-tight sm:text-3xl">
          Creemos que la economía se fortalece una conexión de negocio a la vez — cuando la empresa
          correcta encuentra al comprador correcto, y ambas pueden seguir creciendo.
        </blockquote>

        <div className="mt-14 grid gap-8 text-left sm:grid-cols-3 sm:text-center">
          {pillars.map(({ icon: Icon, title, description }) => (
            <div key={title} className="flex flex-col items-start gap-3 sm:items-center">
              <span className="flex size-11 items-center justify-center rounded-xl bg-white/10">
                <Icon className="size-5 text-brand-lime" />
              </span>
              <h3 className="text-base font-semibold">{title}</h3>
              <p className="text-sm leading-relaxed text-white/70">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function AudienceSection() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-20 sm:py-28">
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-sm font-semibold uppercase tracking-wider text-primary">Para ambos lados del mercado</p>
        <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
          Un solo lugar, dos formas de crecer
        </h2>
        <p className="mt-4 text-muted-foreground">
          Tu empresa puede vender, comprar, o ambas cosas a la vez — lo decides al crear tu perfil, y
          puedes cambiarlo cuando quieras.
        </p>
      </div>

      <div className="mt-16 grid gap-8 lg:grid-cols-2">
        <AudienceCard
          eyebrow="Si vendes"
          title="Proveedores"
          accent="teal"
          benefits={SUPPLIER_BENEFITS}
        />
        <AudienceCard
          eyebrow="Si compras"
          title="Compradores"
          accent="olive"
          benefits={BUYER_BENEFITS}
        />
      </div>
    </section>
  );
}

function AudienceCard({ eyebrow, title, accent, benefits }) {
  const accentClasses = accent === 'teal' ? 'text-brand-teal' : 'text-brand-olive';
  const iconBg = accent === 'teal' ? 'bg-brand-teal/10' : 'bg-brand-olive/10';

  return (
    <div className="rounded-3xl border border-border bg-card p-8 shadow-sm sm:p-10">
      <p className={`text-sm font-semibold uppercase tracking-wider ${accentClasses}`}>{eyebrow}</p>
      <h3 className="mt-2 text-2xl font-bold tracking-tight">{title}</h3>

      <ul className="mt-8 space-y-6">
        {benefits.map(({ icon: Icon, title: benefitTitle, description }) => (
          <li key={benefitTitle} className="flex gap-4">
            <span className={`flex size-10 shrink-0 items-center justify-center rounded-xl ${iconBg}`}>
              <Icon className={`size-5 ${accentClasses}`} />
            </span>
            <div>
              <p className="font-semibold">{benefitTitle}</p>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{description}</p>
            </div>
          </li>
        ))}
      </ul>

      <Button asChild variant="outline" className="mt-8 w-full gap-2 sm:w-auto">
        <Link to="/register">
          Empezar ahora
          <ArrowRight className="size-4" />
        </Link>
      </Button>
    </div>
  );
}

function HowItWorks() {
  return (
    <section id="como-funciona" className="bg-secondary/50 py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-primary">Cómo funciona</p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
            De un perfil a una adjudicación, sin desvíos
          </h2>
        </div>

        <div className="mt-16 grid gap-8 sm:grid-cols-3">
          {STEPS.map(({ number, title, description }, index) => (
            <div key={number} className="relative">
              <span className="text-5xl font-bold text-primary/15">{number}</span>
              <h3 className="mt-3 text-lg font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
              {index < STEPS.length - 1 && (
                <ArrowRight className="absolute right-0 top-3 hidden size-5 -translate-y-1/2 text-border sm:right-[-2rem] sm:block" />
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CategoriesSection() {
  return (
    <section id="categorias" className="mx-auto max-w-7xl px-6 py-20 sm:py-28">
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-sm font-semibold uppercase tracking-wider text-primary">Cobertura</p>
        <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
          Estamos construyendo cobertura en las industrias que mueven a Chile
        </h2>
        <p className="mt-4 text-muted-foreground">
          La clasificación combina qué vende tu empresa con la industria a la que sirve, para que el
          match sea preciso desde el primer resultado.
        </p>
      </div>

      <div className="mt-12 flex flex-wrap justify-center gap-3">
        {CATEGORIES.map(({ label, icon: Icon }) => (
          <span
            key={label}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2 text-sm font-medium text-foreground shadow-sm"
          >
            <Icon className="size-4 text-brand-teal" />
            {label}
          </span>
        ))}
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="relative mx-6 my-4 overflow-hidden rounded-3xl bg-gradient-to-br from-brand-teal to-brand-teal-dark px-6 py-16 text-center text-white sm:mx-auto sm:my-8 sm:max-w-6xl sm:py-20">
      <img
        src={logoIcon}
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute -right-10 -top-10 size-56 opacity-15 sm:size-72"
      />
      <div className="relative mx-auto max-w-2xl">
        <Leaf className="mx-auto size-8 text-brand-lime" aria-hidden="true" />
        <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
          Tu próxima buena relación de negocios empieza con un perfil
        </h2>
        <p className="mt-4 text-white/80">
          Crear tu cuenta toma menos de dos minutos. Sin costo, sin letra chica.
        </p>
        <div className="mt-8">
          <Button asChild size="lg" variant="secondary" className="gap-2">
            <Link to="/register">
              Crear cuenta gratis
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}

function SiteFooter() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-10 sm:flex-row sm:items-center sm:justify-between">
        <Link to="/" className="flex items-center gap-2">
          <img src={logo} alt="Directorio de Empresas" className="h-7 w-auto" />
        </Link>

        <nav className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
          <a href="#como-funciona" className="transition-colors hover:text-foreground">
            Cómo funciona
          </a>
          <a href="#categorias" className="transition-colors hover:text-foreground">
            Categorías
          </a>
          <Link to="/login" className="transition-colors hover:text-foreground">
            Iniciar sesión
          </Link>
          <Link to="/register" className="transition-colors hover:text-foreground">
            Crear cuenta
          </Link>
        </nav>

        <p className="text-sm text-muted-foreground">
          © {new Date().getFullYear()} Directorio de Empresas · Chile
        </p>
      </div>
    </footer>
  );
}
