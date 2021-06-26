# copy supplements and overrides to site-downloads

SRC=/Scrapes/gcf/es-pt/NotFromSite
DST=/Scrapes/gcf/es-pt/site-download

rsync -av $SRC/es-html/ $DST/html/edu.gcfglobal.org/es/
rsync -av $SRC/pt-html/ $DST/html/edu.gcfglobal.org/pt/

rsync -av $SRC/assets/ $DST/es-non-html/media.gcflearnfree.org/global/
rsync -av $SRC/assets/ $DST/pt-non-html/media.gcflearnfree.org/global/

rsync -av $SRC/es-css/ $DST/es-non-html/edu.gcfglobal.org/styles/deployment-es/
rsync -av $SRC/pt-css/ $DST/pt-non-html/edu.gcfglobal.org/styles/deployment-pt/
