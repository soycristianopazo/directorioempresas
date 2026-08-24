import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';

export default function HomePage() {
  const { isAuthenticated, loading } = useAuth();

  return (
    <main className="mx-auto flex min-h-dvh max-w-5xl flex-col px-6">
      <Helmet>
        <title>Directorio de Empresas · Proveedores y abastecimiento B2B</title>
        <meta
          name="description"
          content="Encuentra proveedores verificados, publica requerimientos y gestiona cotizaciones en un solo lugar."
        />
      </Helmet>

      <header className="flex items-center justify-between py-6">
        <span className="font-semibold tracking-tight">Directorio de Empresas</span>
        <nav className="flex items-center gap-2">
          {loading ? null : isAuthenticated ? (
            <Button asChild size="sm">
              <Link to="/dashboard">Ir al panel</Link>
            </Button>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm">
                <Link to="/login">Iniciar sesión</Link>
              </Button>
              <Button asChild size="sm">
                <Link to="/register">Crear cuenta</Link>
              </Button>
            </>
          )}
        </nav>
      </header>

      <section className="flex flex-1 flex-col justify-center py-16">
        <p className="text-sm font-medium text-primary">Abastecimiento B2B</p>
        <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
          Encuentra proveedores confiables. Cotiza, compara y adjudica en un solo lugar.
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-muted-foreground">
          Un ecosistema de empresas verificadas donde el proveedor gana visibilidad y el comprador
          gana tiempo.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Button asChild size="lg">
            <Link to="/register">Registrar mi empresa</Link>
          </Button>
        </div>
      </section>
    </main>
  );
}
