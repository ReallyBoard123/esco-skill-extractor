import { NextRequest, NextResponse } from "next/server"

const JOB_API_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
const API_KEY = "jobboerse-jobsuche"

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const was = searchParams.get("was")
  const wo = searchParams.get("wo")
  const umkreis = searchParams.get("umkreis") || "40"
  const size = searchParams.get("size") || "10"

  if (!was) {
    return NextResponse.json({ error: "Parameter 'was' ist erforderlich" }, { status: 400 })
  }

  const query = new URLSearchParams()
  query.set("was", was)
  if (wo) query.set("wo", wo)
  if (umkreis) query.set("umkreis", umkreis)
  query.set("size", size)
  
  // Add sorting - sort by publication date (newest first)
  query.set("veroeffentlichtseit", "30") // Last 30 days for fresher jobs

  try {
    const response = await fetch(`${JOB_API_URL}?${query.toString()}`, {
      headers: {
        "X-API-Key": API_KEY,
      },
      cache: "no-store",
    })

    if (!response.ok) {
      const text = await response.text()
      return NextResponse.json({ error: text || "Arbeitsagentur API Fehler" }, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    return NextResponse.json({ error: error.message || "Job-Suche fehlgeschlagen" }, { status: 500 })
  }
}
