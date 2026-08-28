"use client";

import React from "react";
import { Autoplay, EffectCoverflow, Pagination } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/react";
import "swiper/css/effect-coverflow";
import "swiper/css/pagination";
import "swiper/css";

import { cn } from "@/lib/utils";

const Carousel_003 = ({
  slides,
  className,
  showPagination = false,
  loop = true,
  autoplay = false,
  spaceBetween = 20,
  perView,
  initialSlide = 0,
}: {
  slides: React.ReactNode[];
  className?: string;
  showPagination?: boolean;
  loop?: boolean;
  autoplay?: boolean;
  spaceBetween?: number;
  /** Slides shown at once. Defaults to all of them (no clipping, no scroll needed). */
  perView?: number;
  initialSlide?: number;
}) => {
  const effectivePerView = perView ?? slides.length;
  // Centering shifts the whole row to keep the active slide in the middle —
  // correct for a peek carousel, but when every slide already fits (perView
  // covers them all) that same shift pushes the last slide out of view.
  const showingAll = effectivePerView >= slides.length;
  const css = `
  .Carousal_003 {
    width: 100%;
    height: 300px;
    padding-bottom: 44px !important;
  }

  .Carousal_003 .swiper-slide {
    display: flex;
    align-items: stretch;
    opacity: 0.65;
    transition: opacity 0.3s ease;
  }

  .Carousal_003 .swiper-slide-active {
    opacity: 1;
  }

  .swiper-pagination-bullet {
    background-color: var(--color-accent) !important;
  }
`;
  return (
    <div className={cn("relative w-full", className)}>
      <style>{css}</style>

      <Swiper
        initialSlide={initialSlide}
        spaceBetween={spaceBetween}
        autoplay={
          autoplay
            ? {
                delay: 2500,
                disableOnInteraction: true,
              }
            : false
        }
        effect="coverflow"
        grabCursor={true}
        slidesPerView={effectivePerView}
        centeredSlides={!showingAll}
        loop={loop}
        coverflowEffect={{
          rotate: 35,
          stretch: 0,
          depth: 120,
          modifier: 1,
          slideShadows: false,
        }}
        pagination={
          showPagination
            ? {
                clickable: true,
              }
            : false
        }
        className="Carousal_003"
        modules={[EffectCoverflow, Autoplay, Pagination]}
      >
        {slides.map((slide, index) => (
          <SwiperSlide key={index}>{slide}</SwiperSlide>
        ))}
      </Swiper>
    </div>
  );
};

export { Carousel_003 };

/**
 * Skiper 49 Carousel_003 — React + Swiper
 * Built with Swiper.js - Read docs to learn more https://swiperjs.com/
 *
 * License & Usage:
 * - Free to use and modify in both personal and commercial projects.
 * - Attribution to Skiper UI is required when using the free version.
 * - No attribution required with Skiper UI Pro.
 *
 * Author: @gurvinder-singh02
 * Website: https://gxuri.me
 * Twitter: https://x.com/Gur__vi
 */
