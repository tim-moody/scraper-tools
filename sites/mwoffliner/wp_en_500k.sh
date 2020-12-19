# docker container logs mwoffliner_wikipedia_en_top_500k
# docker logs -f mwoffliner_wikipedia_en_top_500k
# docker stats
# docker rm mwoffliner_wikipedia_en_top_500k
# docker container ls -a
# ps -ax |grep docker # service or container
# docker inspect -f '{{.State.Pid}}' mwoffliner_wikipedia_en_top_500k
# grep VmPeak /proc/<pid>/status # is this swap?

docker run -v /zim-output:/output:rw \
--name mwoffliner_wikipedia_en_top_500k \
--detach --cpu-shares 3072 --memory-swappiness 0 \
--memory 8g openzim/mwoffliner:1.11.2 mwoffliner \
--adminEmail="info@iiab.me" \
--articleList="http://download.openzim.org/wp1/enwiki/tops/500000.tsv" \
--customZimDescription="Top five hundred thousand Wikipedia articles" \
--customZimFavicon="https://en.wikipedia.org/static/images/project-logos/enwiki.png" \
--customZimTitle="Wikipedia Top 500K" --filenamePrefix="wikipedia_en_top_500k" \
--format="novid:maxi" \
--mwUrl="https://en.wikipedia.org/" \
--osTmpDir="/dev/shm" --outputDirectory="/output" --zstd --webp
