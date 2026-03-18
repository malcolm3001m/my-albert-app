from fastapi import APIRouter, Depends

from app.api.deps import get_courses_service
from app.models.course import (
    CourseInstanceDetailResponse,
    CourseInstanceListResponse,
    CourseListResponse,
    CourseModuleDetailResponse,
)
from app.services.albert.courses_service import CoursesService


router = APIRouter(tags=["courses"])


@router.get("/courses", response_model=CourseListResponse)
async def get_courses(courses_service: CoursesService = Depends(get_courses_service)) -> CourseListResponse:
    return await courses_service.get_courses()


@router.get("/course-instances", response_model=CourseInstanceListResponse)
async def get_course_instances(
    courses_service: CoursesService = Depends(get_courses_service),
) -> CourseInstanceListResponse:
    return await courses_service.get_course_instances()


@router.get("/course-instances/{instance_id}", response_model=CourseInstanceDetailResponse)
async def get_course_instance(
    instance_id: int,
    courses_service: CoursesService = Depends(get_courses_service),
) -> CourseInstanceDetailResponse:
    return CourseInstanceDetailResponse(
        course_instance=await courses_service.get_course_instance(instance_id)
    )


@router.get("/course-modules/{course_module_id}", response_model=CourseModuleDetailResponse)
async def get_course_module(
    course_module_id: int,
    courses_service: CoursesService = Depends(get_courses_service),
) -> CourseModuleDetailResponse:
    return CourseModuleDetailResponse(
        course_module=await courses_service.get_course_module(course_module_id)
    )
