import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Button } from '@/components/ui/button';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 text-center">
      <Helmet>
        <title>Página no encontrada · Directorio de Empresas</title>
      </Helmet>
      <p className="text-sm font-medium text-primary">404</p>
      <h1 className="text-xl font-semibold">No encontramos esta página</h1>
      <Button asChild>
        <Link to="/">Volver al inicio</Link>
      </Button>
    </div>
  );
}
