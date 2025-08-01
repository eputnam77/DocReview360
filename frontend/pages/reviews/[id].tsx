import { useRouter } from "next/router";

export default function ReviewDetailPage() {
  const router = useRouter();
  const { id } = router.query;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Review Details</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">
            Review details for ID: {id} - coming soon.
          </p>
        </div>
      </div>
    </div>
  );
}
