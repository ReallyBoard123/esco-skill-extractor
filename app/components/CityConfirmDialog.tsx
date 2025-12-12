"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { MapPin, CheckCircle, Edit3 } from "lucide-react"

interface CityConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  detectedCity?: string
  detectionReason?: string
  confidence?: number
  onConfirm: (city: string) => void
  onCancel: () => void
}

export function CityConfirmDialog({
  open,
  onOpenChange,
  detectedCity,
  detectionReason,
  confidence,
  onConfirm,
  onCancel
}: CityConfirmDialogProps) {
  const [customCity, setCustomCity] = useState("")
  const [useCustom, setUseCustom] = useState(false)

  const handleConfirm = () => {
    const selectedCity = useCustom ? customCity.trim() : detectedCity || ""
    if (selectedCity) {
      onConfirm(selectedCity)
      onOpenChange(false)
    }
  }

  const handleCancel = () => {
    setUseCustom(false)
    setCustomCity("")
    onCancel()
    onOpenChange(false)
  }

  const popularCities = [
    "Berlin", "München", "Hamburg", "Köln", "Frankfurt", 
    "Stuttgart", "Dresden", "Leipzig", "Hannover", "Dortmund"
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MapPin className="w-5 h-5 text-blue-600" />
            Confirm Job Search Location
          </DialogTitle>
          <DialogDescription>
            We'll search for jobs in your selected city. Please confirm or change the location.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Detected City Option */}
          {detectedCity && (
            <div className={`border rounded-lg p-3 transition-all ${
              !useCustom ? "border-blue-300 bg-blue-50" : "border-gray-200"
            }`}>
              <div className="flex items-center gap-2 mb-2">
                <Button
                  variant={!useCustom ? "default" : "outline"}
                  size="sm"
                  onClick={() => setUseCustom(false)}
                  className="h-8"
                >
                  <CheckCircle className="w-4 h-4 mr-1" />
                  Use Detected
                </Button>
                <span className="font-medium text-gray-900">{detectedCity}</span>
                {confidence && (
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                    {Math.round(confidence * 100)}% confident
                  </span>
                )}
              </div>
              {detectionReason && (
                <p className="text-xs text-gray-600 ml-2">
                  Detected from: {detectionReason}
                </p>
              )}
            </div>
          )}

          {/* Custom City Option */}
          <div className={`border rounded-lg p-3 transition-all ${
            useCustom ? "border-blue-300 bg-blue-50" : "border-gray-200"
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <Button
                variant={useCustom ? "default" : "outline"}
                size="sm"
                onClick={() => setUseCustom(true)}
                className="h-8"
              >
                <Edit3 className="w-4 h-4 mr-1" />
                Choose Different
              </Button>
              <Label htmlFor="custom-city" className="font-medium text-gray-900">
                Enter City Name
              </Label>
            </div>
            <div className="ml-2">
              <Input
                id="custom-city"
                placeholder="e.g. Berlin, München, Hamburg..."
                value={customCity}
                onChange={(e) => setCustomCity(e.target.value)}
                disabled={!useCustom}
                className="mt-1"
              />
              {useCustom && (
                <div className="mt-2">
                  <p className="text-xs text-gray-500 mb-2">Popular cities:</p>
                  <div className="flex flex-wrap gap-1">
                    {popularCities.map((city) => (
                      <button
                        key={city}
                        onClick={() => setCustomCity(city)}
                        className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                      >
                        {city}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <DialogFooter className="flex gap-2 sm:gap-0">
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <Button 
            onClick={handleConfirm}
            disabled={useCustom && !customCity.trim()}
            className="bg-green-600 hover:bg-green-700"
          >
            Search Jobs in {useCustom ? customCity.trim() || "..." : detectedCity || "Selected City"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}