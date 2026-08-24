'use client'

import { useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { publishOrganizationAction } from '@/server/actions/organization'
import { Button } from '@/components/ui/button'
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export function PublishCard({
  organizationId,
  status,
}: {
  organizationId: string
  status: string
}) {
  const router = useRouter()
  const [pending, startTransition] = useTransition()

  const isPublished = status === 'ACTIVE'

  function publish() {
    startTransition(async () => {
      const result = await publishOrganizationAction(organizationId)
      if (result.ok) {
        toast.success('Perfil publicado')
        router.refresh()
      } else {
        toast.error(result.error ?? 'No se pudo publicar')
      }
    })
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle>Publicación</CardTitle>
          <Badge tone={isPublished ? 'success' : 'warning'}>
            {isPublished ? 'Publicado' : 'Borrador'}
          </Badge>
        </div>
        <CardDescription>
          Para publicar necesitas nombre comercial, RUT y ambas descripciones. Un perfil incompleto
          genera resultados con ruido y menos contactos.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button onClick={publish} disabled={pending || isPublished}>
          {isPublished ? 'Perfil publicado' : pending ? 'Publicando…' : 'Publicar perfil'}
        </Button>
      </CardContent>
    </Card>
  )
}
