import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function DexPage() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">DEX</h1>
        <p className="text-muted-foreground">
          Decentralized exchange
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Coming Soon</CardTitle>
          <CardDescription>
            This feature will be available soon
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Please check back later for updates.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export default DexPage;