from setuptools import find_packages, setup

package_name = "create2_driver"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools", "pyserial"],
    zip_safe=True,
    maintainer="Bobby Larson",
    maintainer_email="bobby@mindhive.tech",
    description="ROS 2 driver for iRobot Create 2.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "create2_driver_node = create2_driver.driver_node:main",
            "create2_smoke = create2_driver.smoke:main",
        ],
    },
)
